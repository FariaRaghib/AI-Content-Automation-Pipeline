"""
Stock Photo Fetcher (Pexels)
------------------------------
Fetches a real, free stock photo for the post. No cost, no billing
account needed - just a free Pexels API key.

Search query is kept simple: always "sales", with random selection
among the top results so repeated posts don't all show the same photo.

Run standalone to test:
    python stock_photo_fetcher.py
"""

import os
import random
import requests
from dotenv import load_dotenv

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

OUTPUT_DIR = "data/images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"

# "sales" alone is too ambiguous - stock sites interpret it as retail/shopping
# sales (clothes, shoes, discount tags) rather than B2B sales. These curated
# phrases are unambiguous and stay strictly in the business/corporate context.
BUSINESS_QUERIES = [
    "sales team meeting",
"business analytics",
"startup founders",
"customer acquisition",
"revenue growth",
"business dashboard",
"data analysis",
"sales strategy",
"lead generation",
"business networking",
"CRM software",
"business intelligence",
"professional teamwork",
"digital transformation",
"SaaS startup",
"market research",
"client meeting",
"performance metrics",
"business planning",
"financial analytics",
"technology startup",
"business automation",
"sales presentation",
"executive leadership",
"remote sales team",
"growth strategy",
"business innovation",
"customer success",
"corporate technology",
"entrepreneur workspace",
"B2B sales",
"sales pipeline",
"business growth",
"corporate meeting",
"business professionals",
"data visualization",
"KPI dashboard",
"sales call",
"email marketing",
"prospecting",
"modern office",
"businesswoman laptop",
"businessman working",
"startup office",
"corporate workspace",
"business collaboration",
"executive meeting",
"team brainstorming",
"strategic planning",
"business success",
]


def build_search_query(hook_text="", angle_text=""):
    """Pick a random unambiguous business-context query."""
    return random.choice(BUSINESS_QUERIES)


def fetch_stock_photo(hook_text="", angle_text="", filename="stock_photo.jpg"):
    """Search Pexels and download a randomly-picked photo from the top matches."""
    if not PEXELS_API_KEY:
        raise SystemExit("ERROR: PEXELS_API_KEY not found in .env. Get one free at pexels.com/api")

    query = build_search_query(hook_text, angle_text)

    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 10, "orientation": "square"}

    response = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=15)
    if response.status_code != 200:
        raise Exception(f"Pexels search failed ({response.status_code}): {response.text}")

    photos = response.json().get("photos", [])

    if not photos:
        raise Exception(f"No stock photos found for query: '{query}'.")

    # Pick randomly among the top results (not always #1) for variety across posts
    chosen_photo = random.choice(photos[:min(5, len(photos))])
    image_url = chosen_photo["src"]["large"]

    img_response = requests.get(image_url, timeout=20)
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(img_response.content)

    return filepath, query


if __name__ == "__main__":
    path, query_used = fetch_stock_photo(filename="test_stock.jpg")
    print(f"[OK] Downloaded stock photo using query '{query_used}' -> {path}")