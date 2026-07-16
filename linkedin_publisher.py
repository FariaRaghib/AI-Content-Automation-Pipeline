"""
LinkedIn Publisher
--------------------
Takes today's (or next upcoming) LinkedIn hook from the planner calendar
and posts it directly to LinkedIn as Faria, with:
  - A real, free, topic-matched stock photo (via Pexels)
  - Your website link included in the post text (clickable)

LinkedIn requires the actual image bytes uploaded to their own asset
storage (unlike Instagram, which can take a public URL directly) - so
we download the Pexels photo locally first, then upload it to LinkedIn.

Run:
    python linkedin_publisher.py
"""

import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import requests

from stock_photo_fetcher import fetch_stock_photo

load_dotenv()

LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_PERSON_URN")
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://lead-qualify-ten.vercel.app")

if not LINKEDIN_ACCESS_TOKEN or not LINKEDIN_PERSON_URN:
    raise SystemExit("ERROR: LINKEDIN_ACCESS_TOKEN or LINKEDIN_PERSON_URN missing in .env")

CALENDAR_FILE = "data/planner_calendar.json"
LINKEDIN_API_BASE = "https://api.linkedin.com/v2"


def load_todays_linkedin_post():
    """Get today's LinkedIn post from the calendar, or the next upcoming one."""
    if not os.path.exists(CALENDAR_FILE):
        raise SystemExit(f"ERROR: {CALENDAR_FILE} not found. Run planner.py first.")

    with open(CALENDAR_FILE, encoding='utf-8') as f:
        data = json.load(f)

    calendar = data['calendar']
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    todays_li_posts = [p for p in calendar if p['platform'] == 'linkedin' and p['date'] == today]
    if todays_li_posts:
        return todays_li_posts[0]

    upcoming = [p for p in calendar if p['platform'] == 'linkedin' and p['date'] >= today]
    if upcoming:
        return sorted(upcoming, key=lambda x: x['date'])[0]

    return None


def register_image_upload():
    """Step 1: Tell LinkedIn we want to upload an image, get an upload URL + asset URN."""
    url = f"{LINKEDIN_API_BASE}/assets?action=registerUpload"
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": LINKEDIN_PERSON_URN,
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }
            ]
        }
    }
    response = requests.post(url, headers=headers, json=payload, timeout=20)
    if response.status_code != 200:
        raise Exception(f"Register upload failed: {response.text}")

    result = response.json()
    upload_url = result['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
    asset_urn = result['value']['asset']
    return upload_url, asset_urn


def upload_image_binary(upload_url, image_path):
    """Step 2: Upload the actual image bytes to the URL LinkedIn gave us."""
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}"
    }
    with open(image_path, "rb") as f:
        response = requests.put(upload_url, headers=headers, data=f, timeout=30)
    if response.status_code not in (200, 201):
        raise Exception(f"Image upload failed ({response.status_code}): {response.text}")


def post_to_linkedin_with_image(text, asset_urn):
    """Step 3: Create the actual post, referencing the uploaded image asset."""
    url = f"{LINKEDIN_API_BASE}/ugcPosts"
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    payload = {
        "author": LINKEDIN_PERSON_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": text
                },
                "shareMediaCategory": "IMAGE",
                "media": [
                    {
                        "status": "READY",
                        "media": asset_urn,
                        "title": {
                            "text": "LeadQualify"
                        }
                    }
                ]
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    response = requests.post(url, headers=headers, json=payload, timeout=20)

    if response.status_code == 201:
        return response.headers.get("x-restli-id", "unknown-id")
    else:
        raise Exception(f"LinkedIn post failed ({response.status_code}): {response.text}")


def main():
    print("Loading today's LinkedIn post from calendar...")
    post = load_todays_linkedin_post()

    if not post:
        print("[INFO] No LinkedIn post scheduled today or upcoming. Nothing to publish.")
        return

    hook_text = post['hook']
    angle_text = post.get('angle', '')
    full_text = f"{hook_text}\n\n{post['cta']}\n\nTry it: {WEBSITE_URL}"

    print(f"Post to publish: {hook_text[:60]}...")

    print("Finding a matching stock photo...")
    image_path, query_used = fetch_stock_photo(hook_text, angle_text, filename="linkedin_post.jpg")
    print(f"[OK] Downloaded photo (query: '{query_used}'): {image_path}")

    print("Registering image upload with LinkedIn...")
    upload_url, asset_urn = register_image_upload()

    print("Uploading image...")
    upload_image_binary(upload_url, image_path)
    print(f"[OK] Image uploaded: {asset_urn}")

    print("Publishing post...")
    post_id = post_to_linkedin_with_image(full_text, asset_urn)

    print(f"[OK] Published to LinkedIn! Post ID: {post_id}")


if __name__ == "__main__":
    main()