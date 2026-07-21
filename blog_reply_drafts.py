"""
Blog (dev.to) Reply Draft Generator
--------------------------------------
Reads qualified blog leads from instagram_and_blog_comments_fetcher.py output.
Generates a personalized reply (as Faria) using Google Gemini - same voice
and logic as the Instagram auto-reply script.

IMPORTANT DIFFERENCE FROM INSTAGRAM: dev.to's public API has no endpoint
for creating comments, so this script CANNOT auto-post replies. Instead it
saves drafts to a file (and prints them) so you can copy-paste them onto
dev.to manually, or so your Telegram digest can surface them to you.

SAFETY: Only drafts replies for comments scoring >= 50 (qualified leads).
Skips comments that already have a draft generated (avoids duplicate
drafts on repeated runs) - but since posting is manual, it's on you to
mark a draft as "used" once you've actually posted it (see mark_as_posted
notes at the bottom of this file).

Run:
    python blog_reply_drafts.py
"""

import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import urllib.request

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise SystemExit("ERROR: GOOGLE_API_KEY missing in .env")

GEMINI_MODEL = "gemini-3.5-flash"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GOOGLE_API_KEY}"

COMMENTS_FILE = "data/instagram_and_blog_comments.json"
DRAFTED_LOG_FILE = "data/blog_already_drafted.json"
DRAFTS_OUTPUT_FILE = "data/blog_reply_drafts.json"


def load_qualified_blog_leads():
    if not os.path.exists(COMMENTS_FILE):
        raise SystemExit(f"ERROR: {COMMENTS_FILE} not found. Run instagram_and_blog_comments_fetcher.py first.")
    with open(COMMENTS_FILE, encoding='utf-8') as f:
        data = json.load(f)
    qualified = data.get('qualified_leads', [])
    # Only handle blog comments here - Instagram is handled by instagram_auto_reply.py
    return [lead for lead in qualified if lead.get('platform') == 'blog']


def load_already_drafted():
    """Track which comment IDs we've already generated a draft for, to avoid duplicates."""
    if os.path.exists(DRAFTED_LOG_FILE):
        with open(DRAFTED_LOG_FILE, encoding='utf-8') as f:
            return set(json.load(f))
    return set()


def save_already_drafted(drafted_ids):
    with open(DRAFTED_LOG_FILE, "w", encoding='utf-8') as f:
        json.dump(list(drafted_ids), f, indent=2)


def generate_reply(comment_text, commenter_name):
    """Use Gemini to write a short, personalized reply as Faria (same voice as Instagram)."""
    prompt = f"""You are Faria, founder of LeadQualify (B2B lead scoring AI).

Someone commented on your dev.to blog post: "{comment_text}"
Their username: {commenter_name}

Write a SHORT (1-2 sentence) reply as Faria. Direct, warm, founder voice - not corporate/salesy.
Acknowledge what they said specifically. If it makes sense, naturally invite them to try LeadQualify or DM you.
Do NOT use hashtags. Do NOT be overly formal. This is a developer community, so it's fine to be technical.

Output ONLY the reply text, nothing else."""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 150}
    }

    req = urllib.request.Request(
        GEMINI_API_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode('utf-8'))

    return result['candidates'][0]['content']['parts'][0]['text'].strip()


def main():
    print("Loading qualified blog leads...")
    qualified = load_qualified_blog_leads()
    already_drafted = load_already_drafted()

    new_leads = [lead for lead in qualified if lead['comment_id'] not in already_drafted]

    if not new_leads:
        print("[INFO] No new qualified blog leads to draft replies for (all already handled).")
        return

    print(f"Found {len(new_leads)} new qualified blog leads to draft replies for")

    drafts = []
    for lead in new_leads:
        print(f"\nDrafting reply to {lead['commenter_name']}: \"{lead['comment'][:60]}\"")

        try:
            reply_text = generate_reply(lead['comment'], lead['commenter_name'])
            print(f"  Generated draft: {reply_text}")

            drafts.append({
                "commenter_name": lead['commenter_name'],
                "original_comment": lead['comment'],
                "post_permalink": lead.get('post_permalink'),
                "comment_id": lead['comment_id'],
                "lead_score": lead.get('lead_score'),
                "draft_reply": reply_text,
                "posted": False,  # you flip this manually once you've actually posted it
                "generated_at": datetime.now(timezone.utc).isoformat()
            })

            already_drafted.add(lead['comment_id'])

        except Exception as e:
            print(f"  [FAIL] Could not generate draft: {e}")

    # Append to any existing drafts file rather than overwriting, so drafts
    # from previous runs that haven't been posted yet aren't lost
    existing_drafts = []
    if os.path.exists(DRAFTS_OUTPUT_FILE):
        with open(DRAFTS_OUTPUT_FILE, encoding='utf-8') as f:
            existing_drafts = json.load(f)

    all_drafts = existing_drafts + drafts

    with open(DRAFTS_OUTPUT_FILE, "w", encoding='utf-8') as f:
        json.dump(all_drafts, f, indent=2, ensure_ascii=False)

    save_already_drafted(already_drafted)

    print(f"\n[OK] Generated {len(drafts)} new draft(s)")
    print(f"[OK] Saved -> {DRAFTS_OUTPUT_FILE}")
    print(f"[REMINDER] These are DRAFTS ONLY - dev.to has no API to auto-post comments.")
    print(f"           Copy each draft onto the matching post_permalink manually,")
    print(f"           then mark it posted in {DRAFTS_OUTPUT_FILE} so it doesn't")
    print(f"           get surfaced again in your Telegram digest.")


if __name__ == "__main__":
    main()