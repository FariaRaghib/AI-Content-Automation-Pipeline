"""
Agent 4: Analyst
----------------
Tracks performance across platforms (LinkedIn, Instagram, Blog).
Analyzes what's working, recommends content adjustments.

Instagram + Blog(dev.to) stats are now REAL (pulled live from the APIs).
LinkedIn stats remain mocked until LinkedIn API access is granted.

Run:
    python analyst.py

Required in .env:
    IG_ACCESS_TOKEN         - long-lived User/Page access token with
                              instagram_basic + instagram_manage_insights
    IG_BUSINESS_ACCOUNT_ID  - your Instagram Business Account ID
    DEVTO_API_KEY           - already set up from devto_publisher.py
"""

import os
import json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

CALENDAR_FILE = "data/planner_calendar.json"
OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

GRAPH_API_VERSION = "v21.0"  # bump this if Meta deprecates it — check developers.facebook.com/docs/graph-api/changelog
IG_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
IG_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
DEVTO_API_KEY = os.getenv("DEVTO_API_KEY")


def load_calendar():
    """Load the content calendar."""
    if not os.path.exists(CALENDAR_FILE):
        raise SystemExit(f"ERROR: {CALENDAR_FILE} not found. Run planner.py first.")
    with open(CALENDAR_FILE, encoding='utf-8') as f:
        return json.load(f)


def fetch_instagram_media(limit=25):
    """Pull recent IG media (id, caption, type, native like/comment counts)."""
    if not IG_ACCESS_TOKEN or not IG_BUSINESS_ACCOUNT_ID:
        print("  ! IG_ACCESS_TOKEN / IG_BUSINESS_ACCOUNT_ID missing from .env — skipping Instagram.")
        return []

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{IG_BUSINESS_ACCOUNT_ID}/media"
    params = {
        "fields": "id,caption,timestamp,media_type,like_count,comments_count,permalink",
        "limit": limit,
        "access_token": IG_ACCESS_TOKEN,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except requests.RequestException as e:
        print(f"  ! Failed to fetch Instagram media: {e}")
        return []


def fetch_media_insights(media_id, media_type):
    """
    Pull reach/saved/total_interactions for a single media item.
    Metric availability differs by media_type, so we try a broad set and
    fall back quietly if a metric isn't supported for this post.
    """
    if media_type == "VIDEO" or media_type == "REELS":
        metrics = "reach,saved,total_interactions,plays"
    else:
        metrics = "reach,saved,total_interactions"

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{media_id}/insights"
    params = {"metric": metrics, "access_token": IG_ACCESS_TOKEN}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return {item["name"]: item["values"][0]["value"] for item in data}
    except requests.RequestException:
        # Common for very new posts (<~1hr old) or unsupported metric combos — non-fatal.
        return {}


def fetch_instagram_stats(calendar_data):
    """Build real Instagram performance stats from live Graph API data."""
    media_items = fetch_instagram_media()
    if not media_items:
        return None

    calendar_posts = [p for p in calendar_data.get("calendar", []) if p.get("platform") == "instagram"]

    enriched = []
    for media in media_items:
        insights = fetch_media_insights(media["id"], media.get("media_type", ""))
        reach = insights.get("reach", 0)
        saved = insights.get("saved", 0)
        likes = media.get("like_count", 0) or 0
        comments = media.get("comments_count", 0) or 0
        interactions = insights.get("total_interactions", likes + comments + saved)
        engagement_rate = round(interactions / reach, 4) if reach else None

        matched_angle = None
        matched_format = media.get("media_type", "").lower()
        caption = (media.get("caption") or "")
        for post in calendar_posts:
            hook_snippet = (post.get("hook") or "")[:30]
            if hook_snippet and hook_snippet.lower() in caption.lower():
                matched_angle = post.get("angle")
                break

        enriched.append({
            "media_id": media["id"],
            "caption_snippet": caption[:80],
            "permalink": media.get("permalink"),
            "media_type": media.get("media_type"),
            "reach": reach,
            "likes": likes,
            "comments": comments,
            "saved": saved,
            "engagement_rate": engagement_rate,
            "angle": matched_angle,
        })

    valid = [m for m in enriched if m["engagement_rate"] is not None]
    if not valid:
        return {"raw_posts": enriched, "note": "No posts had usable insights yet (too new or missing permissions)."}

    avg_engagement = round(sum(m["engagement_rate"] for m in valid) / len(valid), 4)
    avg_reach = round(sum(m["reach"] for m in valid) / len(valid))
    avg_saves = round(sum(m["saved"] for m in valid) / len(valid))
    top_post = max(valid, key=lambda m: m["engagement_rate"])

    engagement_by_format = {}
    for m in valid:
        fmt = m["media_type"]
        engagement_by_format.setdefault(fmt, []).append(m["engagement_rate"])
    engagement_by_format = {k: round(sum(v) / len(v), 4) for k, v in engagement_by_format.items()}

    engagement_by_angle = {}
    for m in valid:
        if m["angle"]:
            engagement_by_angle.setdefault(m["angle"], []).append(m["engagement_rate"])
    engagement_by_angle = {k: round(sum(v) / len(v), 4) for k, v in engagement_by_angle.items()}

    return {
        "avg_engagement_rate": avg_engagement,
        "avg_reach": avg_reach,
        "avg_saves": avg_saves,
        "best_performing_angle": top_post.get("angle") or "unmatched",
        "top_post": top_post["caption_snippet"],
        "engagement_by_format": engagement_by_format,
        "engagement_by_angle": engagement_by_angle,
        "raw_posts": enriched,
    }


def fetch_devto_stats():
    """Pull real published-article stats from dev.to."""
    if not DEVTO_API_KEY:
        print("  ! DEVTO_API_KEY missing from .env — skipping blog stats.")
        return None

    url = "https://dev.to/api/articles/me/published"
    headers = {"api-key": DEVTO_API_KEY}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        articles = resp.json()
    except requests.RequestException as e:
        print(f"  ! Failed to fetch dev.to stats: {e}")
        return None

    if not articles:
        return {"note": "No published articles yet on dev.to."}

    total_views = sum(a.get("page_views_count", 0) for a in articles)
    total_reactions = sum(a.get("positive_reactions_count", 0) for a in articles)
    total_comments = sum(a.get("comments_count", 0) for a in articles)
    top_article = max(articles, key=lambda a: a.get("page_views_count", 0))

    return {
        "total_articles": len(articles),
        "avg_views_per_article": round(total_views / len(articles)),
        "avg_reactions_per_article": round(total_reactions / len(articles), 1),
        "avg_comments_per_article": round(total_comments / len(articles), 1),
        "best_topic": top_article.get("title"),
        "top_article_url": top_article.get("url"),
        "top_article_views": top_article.get("page_views_count"),
    }


def mock_linkedin_stats():
    """LinkedIn stats still mocked — no API access yet. Replace once approved."""
    return {
        "avg_engagement_rate": 0.045,
        "avg_reach": 2400,
        "avg_clicks": 180,
        "best_performing_angle": "lead quality over quantity",
        "top_post": "87% of leads never close...",
        "engagement_by_angle": {
            "competitive": 0.052,
            "quality": 0.062,
            "orchestration": 0.038
        },
        "note": "MOCKED — LinkedIn API access not yet granted."
    }


def generate_recommendations(stats):
    """Analyze performance and suggest optimizations, using whatever real/mock stats are available."""
    recommendations = []

    linkedin_stats = stats.get("linkedin")
    if linkedin_stats and linkedin_stats.get("engagement_by_angle"):
        eba = linkedin_stats["engagement_by_angle"]
        if eba.get("quality", 0) > eba.get("competitive", 0):
            recommendations.append({
                "priority": "high",
                "platform": "linkedin",
                "recommendation": "Quality-over-quantity angle is outperforming competitive posts (mocked data — verify once real).",
                "action": "Increase quality-focused posts to 2x/week, reduce competitive angle to 1x/week"
            })

    instagram_stats = stats.get("instagram")
    if instagram_stats and instagram_stats.get("engagement_by_format"):
        fmt = instagram_stats["engagement_by_format"]
        if fmt:
            best_fmt = max(fmt, key=fmt.get)
            recommendations.append({
                "priority": "high",
                "platform": "instagram",
                "recommendation": f"'{best_fmt}' is your best-performing format at {fmt[best_fmt]*100:.1f}% engagement.",
                "action": f"Shift more upcoming posts toward {best_fmt} format"
            })
        recommendations.append({
            "priority": "medium",
            "platform": "instagram",
            "recommendation": f"Current avg engagement rate: {instagram_stats['avg_engagement_rate']*100:.1f}% across {len(instagram_stats.get('raw_posts', []))} recent posts.",
            "action": "Review top_post in analyst_output.json and repurpose its hook/angle for next week"
        })
    elif instagram_stats and instagram_stats.get("note"):
        recommendations.append({
            "priority": "low",
            "platform": "instagram",
            "recommendation": instagram_stats["note"],
            "action": "Re-run analyst.py in 24-48h once posts have accumulated reach data"
        })

    blog_stats = stats.get("blog")
    if blog_stats and blog_stats.get("total_articles"):
        recommendations.append({
            "priority": "high",
            "platform": "blog",
            "recommendation": f"Top article '{blog_stats['best_topic']}' got {blog_stats['top_article_views']} views — this topic resonates.",
            "action": "Write a follow-up or deep-dive post on the same topic/keyword cluster"
        })
    elif blog_stats and blog_stats.get("note"):
        recommendations.append({
            "priority": "low",
            "platform": "blog",
            "recommendation": blog_stats["note"],
            "action": "Publish your first live article via devto_publisher.py, then re-run analyst.py"
        })

    if instagram_stats and instagram_stats.get("top_post") and blog_stats:
        recommendations.append({
            "priority": "high",
            "platform": "cross-platform",
            "recommendation": "Repurpose your top-performing Instagram post into a full blog post for SEO + backlinks.",
            "action": f"Turn '{instagram_stats['top_post']}' into a dev.to article"
        })

    return recommendations


def main():
    print("Loading content calendar...")
    calendar_data = load_calendar()

    print("Fetching Instagram stats (live)...")
    instagram_stats = fetch_instagram_stats(calendar_data)

    print("Fetching dev.to blog stats (live)...")
    blog_stats = fetch_devto_stats()

    print("Loading LinkedIn stats (mocked — no API access yet)...")
    linkedin_stats = mock_linkedin_stats()

    stats = {
        "linkedin": linkedin_stats,
        "instagram": instagram_stats,
        "blog": blog_stats,
    }

    print("Generating recommendations...\n")
    recommendations = generate_recommendations(stats)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platform_stats": stats,
        "recommendations": recommendations,
        "note": "Instagram + Blog(dev.to) stats are LIVE. LinkedIn is still mocked pending API access.",
    }

    analysis_path = os.path.join(OUTPUT_DIR, "analyst_output.json")
    with open(analysis_path, "w", encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Saved analysis -> {analysis_path}\n")

    print("--- PERFORMANCE ANALYSIS & RECOMMENDATIONS ---\n")
    if instagram_stats and instagram_stats.get("avg_engagement_rate") is not None:
        print(f"Instagram: {instagram_stats['avg_engagement_rate']*100:.1f}% engagement, {instagram_stats['avg_reach']} avg reach (LIVE)")
    if blog_stats and blog_stats.get("avg_views_per_article"):
        print(f"Blog: {blog_stats['avg_views_per_article']} avg views/article (LIVE)")
    print(f"LinkedIn: {linkedin_stats['avg_engagement_rate']*100:.1f}% engagement (MOCKED)\n")

    print("RECOMMENDATIONS (Prioritized)\n")
    for i, rec in enumerate(recommendations, 1):
        marker = "[HIGH]" if rec['priority'] == "high" else "[MED]" if rec['priority'] == "medium" else "[LOW]"
        print(f"{i}. {marker} [{rec['platform'].upper()}]")
        print(f"   {rec['recommendation']}")
        print(f"   Action: {rec['action']}\n")


if __name__ == "__main__":
    main()