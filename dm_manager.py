"""
Agent 5: DM Manager
-------------------
Monitors comments across platforms.
Flags qualified leads for follow-up.
Suggests reply templates.

Instagram comments are now REAL (pulled live from Graph API).
LinkedIn comments remain mocked until LinkedIn API access is granted.

Note: Instagram doesn't expose a commenter's job title/company like the old
LinkedIn mock did, so IG leads are scored on comment CONTENT signals
(pain points, competitor mentions, demo requests) rather than title.

Run:
    python dm_manager.py

Required in .env:
    IG_ACCESS_TOKEN         - long-lived token with instagram_manage_comments
    IG_BUSINESS_ACCOUNT_ID  - your Instagram Business Account ID
"""

import os
import json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

GRAPH_API_VERSION = "v21.0"  # bump if Meta deprecates it
IG_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
IG_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")

LINKEDIN_URL = "https://www.linkedin.com/in/fariaraghib"

PAIN_POINT_PHRASES = [
    "waste", "wasting", "never close", "never convert", "struggle", "struggling",
    "problem", "pain", "frustrated", "too much time", "manual", "graveyard"
]
COMPETITOR_NAMES = ["apollo", "clay", "hubspot", "salesforce", "zoominfo", "outreach.io", "salesloft"]
DEMO_KEYWORDS = ["demo", "show me", "interested", "pricing", "price", "how much", "book a call"]


def fetch_instagram_media(limit=25):
    """Pull recent IG media IDs + captions/hooks to fetch comments against."""
    if not IG_ACCESS_TOKEN or not IG_BUSINESS_ACCOUNT_ID:
        print("  ! IG_ACCESS_TOKEN / IG_BUSINESS_ACCOUNT_ID missing from .env — skipping Instagram.")
        return []

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{IG_BUSINESS_ACCOUNT_ID}/media"
    params = {
        "fields": "id,caption,timestamp",
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


def fetch_media_comments(media_id):
    """Pull comments for a single media item."""
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{media_id}/comments"
    params = {
        "fields": "id,text,username,timestamp,like_count",
        "access_token": IG_ACCESS_TOKEN,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except requests.RequestException as e:
        print(f"  ! Failed to fetch comments for media {media_id}: {e}")
        return []


def detect_signals(text):
    """Detect content signals in a comment's text since IG has no title/company data."""
    text_lower = text.lower()
    signals = []

    if any(phrase in text_lower for phrase in PAIN_POINT_PHRASES):
        signals.append("pain point mentioned")
    if any(name in text_lower for name in COMPETITOR_NAMES):
        signals.append("competitor mention")
    if any(kw in text_lower for kw in DEMO_KEYWORDS):
        signals.append("demo/pricing interest")
    if len(text_lower) > 60:
        signals.append("detailed engagement")

    return signals


def fetch_instagram_comments():
    """Build real comment list from live Instagram Graph API data."""
    media_items = fetch_instagram_media()
    all_comments = []

    for media in media_items:
        hook = (media.get("caption") or "")[:60]
        comments = fetch_media_comments(media["id"])
        for c in comments:
            text = c.get("text", "")
            signals = detect_signals(text)
            all_comments.append({
                "platform": "instagram",
                "post_id": media["id"],
                "comment_id": c.get("id"),
                "hook": hook,
                "commenter_name": c.get("username", "unknown"),
                "commenter_title": None,  # not available via IG API
                "comment": text,
                "like_count": c.get("like_count", 0),
                "signals": signals,
            })

    return all_comments


def mock_linkedin_comments():
    """LinkedIn comments still mocked — no API access yet."""
    return [
        {
            "platform": "linkedin",
            "post_id": "post_1",
            "hook": "87% of leads never close...",
            "commenter_name": "Sarah Chen",
            "commenter_title": "SDR Manager @ TechCorp",
            "comment": "This is exactly our problem. We're spending 60% of time on leads that never convert.",
            "engagement": "high",
            "signals": ["pain point mentioned", "title suggests buying power", "active engagement"]
        },
        {
            "platform": "linkedin",
            "post_id": "post_2",
            "hook": "Your lead scoring is wrong...",
            "commenter_name": "Mike Rodriguez",
            "commenter_title": "VP Sales @ MidMarket Corp",
            "comment": "How does this compare to Apollo? We're currently using them.",
            "engagement": "high",
            "signals": ["competitor mention", "C-level title", "active buyer"]
        },
    ]


def qualify_leads(comments):
    """
    Score each commenter as a potential lead.
    LinkedIn comments (have commenter_title) use title + engagement scoring.
    Instagram comments (no title) use content-signal scoring only.
    """
    qualified = []

    for comment in comments:
        score = 0
        signals = comment.get("signals", [])

        if comment.get("commenter_title"):
            title = comment["commenter_title"]
            if "VP" in title or "C-level" in title:
                score += 40
            elif "Manager" in title:
                score += 25
            elif "Founder" in title:
                score += 15
            else:
                score += 5

            engagement = comment.get("engagement", "low")
            if engagement == "high":
                score += 30
            elif engagement == "medium":
                score += 15
        else:
            # Instagram / no-title path — score purely on content signals
            score += min(comment.get("like_count", 0) * 2, 20)

        if "pain point mentioned" in signals:
            score += 20
        if "competitor mention" in signals:
            score += 25
        if "demo/pricing interest" in signals or "demo request" in signals:
            score += 20
        if "detailed engagement" in signals:
            score += 10

        comment["lead_score"] = score
        comment["qualified"] = score >= 40  # lower bar than before since IG has no title boost

        if comment["qualified"]:
            qualified.append(comment)

    return sorted(qualified, key=lambda x: x["lead_score"], reverse=True)


def generate_reply_templates(qualified_lead):
    """Generate a personalized reply template for the commenter."""
    name = qualified_lead["commenter_name"].split()[0] if qualified_lead.get("commenter_name") else "there"
    comment = qualified_lead.get("comment", "")

    templates = {
        "default": f"""Hi {name},

Exactly — this is what we built LeadQualify to solve.

I'd love to show you how we identify the leads that actually close, instead of wasting time on the rest.

Message me on LinkedIn and I'll walk you through it: {LINKEDIN_URL}

— Faria""",

        "competitor_comparison": f"""Hi {name},

Great question. Most tools score for fit, not buying intent — LeadQualify optimizes specifically for close probability.

If you're already using another tool, a quick side-by-side might be eye-opening. Message me on LinkedIn: {LINKEDIN_URL}

— Faria""",

        "demo_request": f"""Hi {name},

Love the energy!

Demo coming right up — we'll show you exactly which of your leads are worth pursuing. Message me on LinkedIn to set it up: {LINKEDIN_URL}

— Faria"""
    }

    comment_lower = comment.lower()
    if any(name in comment_lower for name in COMPETITOR_NAMES):
        return templates["competitor_comparison"]
    elif any(kw in comment_lower for kw in DEMO_KEYWORDS):
        return templates["demo_request"]
    else:
        return templates["default"]


def main():
    print("Fetching Instagram comments (live)...")
    instagram_comments = fetch_instagram_comments()

    print("Loading LinkedIn comments (mocked — no API access yet)...")
    linkedin_comments = mock_linkedin_comments()

    all_comments = instagram_comments + linkedin_comments

    print("Qualifying leads from comments...\n")
    qualified = qualify_leads(all_comments)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_comments": len(all_comments),
        "qualified_leads": qualified,
        "note": "Instagram comments are LIVE. LinkedIn comments are still mocked pending API access.",
    }

    leads_path = os.path.join(OUTPUT_DIR, "dm_manager_leads.json")
    with open(leads_path, "w", encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Saved leads -> {leads_path}\n")

    print("--- QUALIFIED LEADS FROM COMMENTS ---\n")
    print(f"Found {len(qualified)} qualified leads from {len(all_comments)} comments.\n")

    for i, lead in enumerate(qualified, 1):
        title_str = f" ({lead['commenter_title']})" if lead.get("commenter_title") else ""
        print(f"{i}. {lead['commenter_name']}{title_str}")
        print(f"   Platform: {lead['platform'].upper()}")
        print(f"   Lead Score: {lead['lead_score']}/100")
        print(f"   Comment: \"{lead['comment']}\"")
        print(f"   Signals: {', '.join(lead['signals'])}")
        print(f"\n   Reply Template:")
        reply = generate_reply_templates(lead)
        for line in reply.split('\n'):
            print(f"   {line}")
        print()


if __name__ == "__main__":
    main()