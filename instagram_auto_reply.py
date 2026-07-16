"""
Instagram Auto-Reply
----------------------
Reads qualified leads from instagram_comments_fetcher.py output.
Generates a personalized reply (as Faria) using Google Gemini.
Posts the reply directly on Instagram via Graph API.

SAFETY: Only replies to comments scoring >= 50 (qualified leads).
Skips comments that already have a reply from you (avoids double-replying
on repeated runs).

Run:
    python instagram_auto_reply.py
"""

import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import requests
import urllib.request

load_dotenv()

INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not INSTAGRAM_ACCESS_TOKEN:
    raise SystemExit("ERROR: INSTAGRAM_ACCESS_TOKEN missing in .env")
if not GOOGLE_API_KEY:
    raise SystemExit("ERROR: GOOGLE_API_KEY missing in .env")

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"
GEMINI_MODEL = "gemini-3.5-flash"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GOOGLE_API_KEY}"

COMMENTS_FILE = "data/instagram_real_comments.json"
REPLIED_LOG_FILE = "data/already_replied.json"


def load_qualified_leads():
    if not os.path.exists(COMMENTS_FILE):
        raise SystemExit(f"ERROR: {COMMENTS_FILE} not found. Run instagram_comments_fetcher.py first.")
    with open(COMMENTS_FILE, encoding='utf-8') as f:
        data = json.load(f)
    return data.get('qualified_leads', [])


def load_already_replied():
    """Track which comment IDs we've already replied to, to avoid duplicates."""
    if os.path.exists(REPLIED_LOG_FILE):
        with open(REPLIED_LOG_FILE, encoding='utf-8') as f:
            return set(json.load(f))
    return set()


def save_already_replied(replied_ids):
    with open(REPLIED_LOG_FILE, "w", encoding='utf-8') as f:
        json.dump(list(replied_ids), f, indent=2)


def generate_reply(comment_text, commenter_name):
    """Use Gemini to write a short, personalized reply as Faria."""
    prompt = f"""You are Faria, founder of LeadQualify (B2B lead scoring AI).

Someone commented on your Instagram post: "{comment_text}"
Their username: {commenter_name}

Write a SHORT (1-2 sentence) reply as Faria. Direct, warm, founder voice - not corporate/salesy.
Acknowledge what they said specifically. If it makes sense, naturally invite them to try LeadQualify or DM you.
Do NOT use hashtags. Do NOT be overly formal.

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


def post_reply(comment_id, reply_text):
    """Post the reply on Instagram."""
    url = f"{GRAPH_API_BASE}/{comment_id}/replies"
    payload = {
        "message": reply_text,
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }
    response = requests.post(url, data=payload, timeout=15)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Reply failed: {response.text}")


def main():
    print("Loading qualified leads...")
    qualified = load_qualified_leads()
    already_replied = load_already_replied()

    new_leads = [lead for lead in qualified if lead['comment_id'] not in already_replied]

    if not new_leads:
        print("[INFO] No new qualified leads to reply to (all already handled).")
        return

    print(f"Found {len(new_leads)} new qualified leads to reply to")

    for lead in new_leads:
        print(f"\nReplying to {lead['commenter_name']}: \"{lead['comment'][:60]}\"")

        try:
            reply_text = generate_reply(lead['comment'], lead['commenter_name'])
            print(f"  Generated reply: {reply_text}")

            post_reply(lead['comment_id'], reply_text)
            print(f"  [OK] Reply posted")

            already_replied.add(lead['comment_id'])

        except Exception as e:
            print(f"  [FAIL] Could not reply: {e}")

    save_already_replied(already_replied)
    print(f"\n[OK] Done. Total comments ever replied to: {len(already_replied)}")


if __name__ == "__main__":
    main()
