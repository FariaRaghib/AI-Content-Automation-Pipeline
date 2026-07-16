"""
Instagram Comment Fetcher
--------------------------
Pulls real comments from your recent Instagram posts via Meta Graph API.
Saves them in a format dm_manager.py can score.

Honest limitation: Instagram's public API does NOT expose a commenter's
job title (that requires LinkedIn-style professional data, which Instagram
doesn't have). So real-comment scoring relies on comment TEXT signals only
(mentions of demo/pricing/competitors/pain points), not title-based scoring
like the original mock data used.

Run:
    python instagram_comments_fetcher.py
"""

import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import requests

load_dotenv()

INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")

if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_BUSINESS_ACCOUNT_ID:
    raise SystemExit("ERROR: INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_BUSINESS_ACCOUNT_ID missing in .env")

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"
OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_recent_media(limit=10):
    """Get your recent Instagram posts (media objects)."""
    url = f"{GRAPH_API_BASE}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
    params = {
        "fields": "id,caption,timestamp,permalink",
        "limit": limit,
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }
    response = requests.get(url, params=params, timeout=15)
    if response.status_code != 200:
        raise Exception(f"Failed to get media: {response.text}")
    return response.json().get("data", [])


def get_comments_for_media(media_id):
    """Get comments on a specific post."""
    url = f"{GRAPH_API_BASE}/{media_id}/comments"
    params = {
        "fields": "id,text,username,timestamp,like_count",
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }
    response = requests.get(url, params=params, timeout=15)
    if response.status_code != 200:
        # Some posts may have comments disabled or other minor errors - don't crash the whole run
        print(f"[WARN] Could not fetch comments for media {media_id}: {response.text}")
        return []
    return response.json().get("data", [])


def score_comment_text_only(text, like_count=0):
    """
    Score a comment based on TEXT SIGNALS ONLY, since Instagram doesn't
    expose commenter job titles the way LinkedIn does.
    """
    score = 0
    signals = []
    text_lower = text.lower()

    high_intent_phrases = ["demo", "pricing", "price", "how much", "integrate", "trial"]
    pain_phrases = ["problem", "stuck", "issue", "struggling", "waste", "wasting"]
    competitor_phrases = ["apollo", "clay", "warmly", "hubspot", "salesforce"]

    if any(p in text_lower for p in high_intent_phrases):
        score += 35
        signals.append("high-intent phrase (demo/pricing/trial)")

    if any(p in text_lower for p in pain_phrases):
        score += 25
        signals.append("pain point mentioned")

    if any(p in text_lower for p in competitor_phrases):
        score += 25
        signals.append("competitor mentioned")

    if like_count and like_count > 2:
        score += 10
        signals.append("comment has engagement (likes)")

    if len(text) > 60:
        score += 10
        signals.append("thoughtful/detailed comment")

    return score, signals


def main():
    print("Fetching recent Instagram posts...")
    media_items = get_recent_media()
    print(f"Found {len(media_items)} recent posts")

    all_comments = []

    for media in media_items:
        media_id = media['id']
        comments = get_comments_for_media(media_id)

        for c in comments:
            text = c.get('text', '')
            like_count = c.get('like_count', 0)
            score, signals = score_comment_text_only(text, like_count)

            all_comments.append({
                "platform": "instagram",
                "post_id": media_id,
                "post_permalink": media.get('permalink'),
                "comment_id": c['id'],
                "commenter_name": c.get('username', 'unknown'),
                "comment": text,
                "like_count": like_count,
                "lead_score": score,
                "qualified": score >= 50,
                "signals": signals,
                "timestamp": c.get('timestamp')
            })

    qualified = [c for c in all_comments if c['qualified']]
    qualified = sorted(qualified, key=lambda x: x['lead_score'], reverse=True)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_comments_scanned": len(all_comments),
        "qualified_leads": qualified,
        "all_comments": all_comments,
        "note": "Scored on comment TEXT only - Instagram API doesn't expose commenter job titles"
    }

    output_path = os.path.join(OUTPUT_DIR, "instagram_real_comments.json")
    with open(output_path, "w", encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"[OK] Scanned {len(all_comments)} comments, found {len(qualified)} qualified leads")
    print(f"[OK] Saved -> {output_path}")

    for lead in qualified[:5]:
        print(f"\n  {lead['commenter_name']} (score: {lead['lead_score']})")
        print(f"  \"{lead['comment'][:80]}\"")
        print(f"  Signals: {', '.join(lead['signals'])}")


if __name__ == "__main__":
    main()
