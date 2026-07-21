"""
Instagram + Blog (dev.to) Comment Fetcher
-------------------------------------------
Pulls real comments from:
  - Instagram (Meta Graph API)
  - dev.to / Forem blog posts (public Comments API)

Saves everything in one unified format that dm_manager.py can score,
tagged per-item with "platform" so downstream nodes can tell them apart.

LinkedIn is intentionally left out for now (pending Community Management
API approval) - add it back in later once that access comes through.

Honest limitation: neither Instagram nor dev.to expose a commenter's job
title, so scoring relies on comment TEXT signals only (mentions of
demo/pricing/competitors/pain points), not title-based scoring.

Run:
    python instagram_and_blog_comments_fetcher.py
"""

import os
import re
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import requests

load_dotenv()

# ---------- Instagram config ----------
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
GRAPH_API_BASE = "https://graph.facebook.com/v19.0"

# ---------- dev.to (blog) config ----------
DEVTO_USERNAME = os.getenv("DEVTO_USERNAME")  # e.g. "fariaraghib" - no API key needed for public reads
DEVTO_API_BASE = "https://dev.to/api"

OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================================================
# Shared scoring logic (text-only signals, no job titles)
# =========================================================
def score_comment_text_only(text, like_count=0):
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


# =========================================================
# Instagram
# =========================================================
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
    """Get comments on a specific Instagram post."""
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


def fetch_instagram_comments():
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_BUSINESS_ACCOUNT_ID:
        print("[SKIP] Instagram: INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_BUSINESS_ACCOUNT_ID missing in .env")
        return []

    print("Fetching recent Instagram posts...")
    media_items = get_recent_media()
    print(f"Found {len(media_items)} recent Instagram posts")

    results = []
    for media in media_items:
        media_id = media['id']
        comments = get_comments_for_media(media_id)

        for c in comments:
            text = c.get('text', '')
            like_count = c.get('like_count', 0)
            score, signals = score_comment_text_only(text, like_count)

            results.append({
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

    print(f"[OK] Instagram: scanned {len(results)} comments")
    return results


# =========================================================
# dev.to / Forem blog
# =========================================================
def flatten_devto_comments(comment_node, flat_list):
    """dev.to comments come back as a nested tree - flatten it recursively."""
    flat_list.append(comment_node)
    for child in comment_node.get("children", []):
        flatten_devto_comments(child, flat_list)


def fetch_devto_comments():
    if not DEVTO_USERNAME:
        print("[SKIP] Blog (dev.to): DEVTO_USERNAME missing in .env")
        return []

    print("Fetching recent dev.to articles...")
    url = f"{DEVTO_API_BASE}/articles"
    params = {"username": DEVTO_USERNAME, "per_page": 10}
    headers = {"User-Agent": "leadqualify-comment-fetcher"}
    response = requests.get(url, params=params, headers=headers, timeout=15)
    if response.status_code != 200:
        print(f"[WARN] dev.to: failed to get articles: {response.text}")
        return []

    articles = response.json()
    print(f"Found {len(articles)} recent dev.to articles")

    results = []
    for article in articles:
        article_id = article["id"]
        c_url = f"{DEVTO_API_BASE}/comments"
        c_params = {"a_id": article_id}
        c_resp = requests.get(c_url, params=c_params, headers=headers, timeout=15)
        if c_resp.status_code != 200:
            print(f"[WARN] dev.to: could not fetch comments for article {article_id}: {c_resp.text}")
            continue

        flat_comments = []
        for top_level in c_resp.json():
            flatten_devto_comments(top_level, flat_comments)

        for c in flat_comments:
            user = c.get("user", {})
            raw_text = c.get("body_html", "") or ""
            plain_text = re.sub("<[^<]+?>", "", raw_text).strip()

            score, signals = score_comment_text_only(plain_text)
            results.append({
                "platform": "blog",
                "post_id": article_id,
                "post_permalink": article.get("url"),
                "comment_id": c.get("id_code", c.get("id")),
                "commenter_name": user.get("username", "unknown"),
                "comment": plain_text,
                "like_count": 0,  # dev.to comments API doesn't expose like counts
                "lead_score": score,
                "qualified": score >= 50,
                "signals": signals,
                "timestamp": None
            })

    print(f"[OK] Blog (dev.to): scanned {len(results)} comments")
    return results


# =========================================================
# Main
# =========================================================
def main():
    all_comments = []
    all_comments.extend(fetch_instagram_comments())
    all_comments.extend(fetch_devto_comments())

    qualified = [c for c in all_comments if c['qualified']]
    qualified = sorted(qualified, key=lambda x: x['lead_score'], reverse=True)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_comments_scanned": len(all_comments),
        "qualified_leads": qualified,
        "all_comments": all_comments,
        "note": "Scored on comment TEXT only - neither platform exposes commenter job titles. LinkedIn left out for now, pending API approval."
    }

    output_path = os.path.join(OUTPUT_DIR, "instagram_and_blog_comments.json")
    with open(output_path, "w", encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Scanned {len(all_comments)} comments total, found {len(qualified)} qualified leads")
    print(f"[OK] Saved -> {output_path}")

    for lead in qualified[:5]:
        print(f"\n  [{lead['platform']}] {lead['commenter_name']} (score: {lead['lead_score']})")
        print(f"  \"{lead['comment'][:80]}\"")
        print(f"  Signals: {', '.join(lead['signals'])}")


if __name__ == "__main__":
    main()