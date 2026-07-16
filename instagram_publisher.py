"""
Instagram Publisher
--------------------
1. Takes today's Instagram hook from the planner calendar
2. Fetches a real, free, topic-matched stock photo (via Pexels)
3. Posts to Instagram via Meta Graph API (2-step: create container -> publish)

Setup needed in .env:
    INSTAGRAM_ACCESS_TOKEN=...
    INSTAGRAM_BUSINESS_ACCOUNT_ID=...
    PEXELS_API_KEY=...   (free, see stock_photo_fetcher.py docstring)

Note: Instagram's API needs a publicly reachable image URL, but Pexels
photos are already hosted on Pexels' own servers - so unlike the old
quote-card approach, we DON'T need a separate image-hosting upload step.
We just pass Pexels' own image URL directly to Instagram.

Run:
    python instagram_publisher.py
"""

import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import requests

from stock_photo_fetcher import build_search_query

load_dotenv()

INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_BUSINESS_ACCOUNT_ID:
    raise SystemExit("ERROR: INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_BUSINESS_ACCOUNT_ID missing in .env")

if not PEXELS_API_KEY:
    raise SystemExit("ERROR: PEXELS_API_KEY missing in .env. Get a free one at pexels.com/api")

CALENDAR_FILE = "data/planner_calendar.json"
GRAPH_API_BASE = "https://graph.facebook.com/v19.0"
PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"


def load_todays_instagram_post():
    """Get today's Instagram post from the calendar, or the next upcoming one."""
    if not os.path.exists(CALENDAR_FILE):
        raise SystemExit(f"ERROR: {CALENDAR_FILE} not found. Run planner.py first.")

    with open(CALENDAR_FILE, encoding='utf-8') as f:
        data = json.load(f)

    calendar = data['calendar']
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    todays_ig_posts = [p for p in calendar if p['platform'] == 'instagram' and p['date'] == today]
    if todays_ig_posts:
        return todays_ig_posts[0]

    upcoming = [p for p in calendar if p['platform'] == 'instagram' and p['date'] >= today]
    if upcoming:
        return sorted(upcoming, key=lambda x: x['date'])[0]

    return None


def get_pexels_image_url(hook_text="", angle_text=""):
    """Search Pexels and return a direct, publicly-hosted image URL (no download needed)."""
    import random

    query = build_search_query(hook_text, angle_text)

    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 10, "orientation": "square"}

    response = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=15)
    if response.status_code != 200:
        raise Exception(f"Pexels search failed ({response.status_code}): {response.text}")

    photos = response.json().get("photos", [])

    if not photos:
        raise Exception(f"No stock photos found for query: '{query}'.")

    chosen_photo = random.choice(photos[:min(5, len(photos))])
    return chosen_photo["src"]["large"], query


def create_media_container(image_url, caption):
    """Step 1: Create the media container on Instagram."""
    url = f"{GRAPH_API_BASE}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }
    response = requests.post(url, data=payload, timeout=30)

    if response.status_code == 200:
        return response.json()['id']
    else:
        raise Exception(f"Media container creation failed: {response.text}")


def publish_media(container_id):
    """Step 2: Publish the created media container."""
    url = f"{GRAPH_API_BASE}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"
    payload = {
        "creation_id": container_id,
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }
    response = requests.post(url, data=payload, timeout=30)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Publish failed: {response.text}")


def main():
    print("Loading today's Instagram post from calendar...")
    post = load_todays_instagram_post()

    if not post:
        print("[INFO] No Instagram post scheduled today or upcoming. Nothing to publish.")
        return

    hook_text = post['hook']
    angle_text = post.get('angle', '')
    caption = f"{post['hook']}\n\n{post['cta']}\n\n#leadscoring #b2bsales #salestech #leadqualify"

    print(f"Post to publish: {hook_text[:60]}...")

    print("Finding a matching stock photo...")
    image_url, query_used = get_pexels_image_url(hook_text, angle_text)
    print(f"[OK] Found photo (query: '{query_used}'): {image_url}")

    print("Creating Instagram media container...")
    container_id = create_media_container(image_url, caption)
    print(f"[OK] Container created: {container_id}")

    print("Publishing to Instagram...")
    result = publish_media(container_id)
    print(f"[OK] Published! Post ID: {result.get('id')}")


if __name__ == "__main__":
    main()