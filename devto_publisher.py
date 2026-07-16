"""
Agent 7: Dev.to Publisher
-------------------------
Takes blog drafts from blog_agent.py (data/blog_agent_drafts.json)
and publishes them to dev.to via their REST API.

Keeps a log (data/devto_published_log.json) of what's already been
published so re-running this script doesn't create duplicate posts.

By default, posts are pushed to dev.to as UNPUBLISHED DRAFTS
(published: false) so you can review/tweak in the dev.to editor
before they go live. Once you trust the pipeline, set
DEVTO_AUTO_PUBLISH=true in .env to have it publish live immediately.

Setup:
    1. Get your API key: dev.to -> Settings -> Extensions -> DEV API Keys
    2. Add to .env:
         DEVTO_API_KEY=your_key_here
         DEVTO_AUTO_PUBLISH=false   (optional, defaults to false)

Run:
    python devto_publisher.py
"""

import os
import json
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
DRAFTS_FILE = os.path.join(DATA_DIR, "blog_agent_drafts.json")
PUBLISHED_LOG_FILE = os.path.join(DATA_DIR, "devto_published_log.json")
ENV_FILE = os.path.join(PROJECT_DIR, ".env")

DEVTO_API_URL = "https://dev.to/api/articles"


def load_env():
    """Load DEVTO_API_KEY / DEVTO_AUTO_PUBLISH from real env vars or .env file."""
    env = {}

    # Try python-dotenv first if it's installed and already loaded into os.environ
    api_key = os.environ.get("DEVTO_API_KEY")
    auto_publish = os.environ.get("DEVTO_AUTO_PUBLISH")

    # Fallback: manually parse .env if vars aren't already in the environment
    if (not api_key or not auto_publish) and os.path.exists(ENV_FILE):
        with open(ENV_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key == "DEVTO_API_KEY" and not api_key:
                    api_key = value
                if key == "DEVTO_AUTO_PUBLISH" and not auto_publish:
                    auto_publish = value

    env["api_key"] = api_key
    env["auto_publish"] = str(auto_publish).lower() == "true" if auto_publish else False
    return env


def load_drafts():
    if not os.path.exists(DRAFTS_FILE):
        raise SystemExit(f"ERROR: {DRAFTS_FILE} not found. Run blog_agent.py first.")
    with open(DRAFTS_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_published_log():
    if not os.path.exists(PUBLISHED_LOG_FILE):
        return {"published_slugs": []}
    with open(PUBLISHED_LOG_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_published_log(log):
    with open(PUBLISHED_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def sanitize_tags(keywords):
    """
    dev.to rules: max 4 tags, alphanumeric only (no spaces or hyphens
    inside a single tag), lowercase.
    """
    tags = []
    for kw in keywords[:4]:
        tag = re.sub(r"[^a-zA-Z0-9]", "", kw)
        if tag:
            tags.append(tag.lower())
    # dedupe while preserving order
    seen = set()
    deduped = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    return deduped[:4]


def publish_to_devto(blog_post, api_key, publish_live):
    meta = blog_post["metadata"]

    payload = {
        "article": {
            "title": meta["title"],
            "published": publish_live,
            "body_markdown": blog_post["draft_markdown"],
            "tags": sanitize_tags(meta.get("keywords", [])),
            "description": meta.get("meta_description", "")[:160],
        }
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        DEVTO_API_URL,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "api-key": api_key,
            # dev.to's API silently 403s POST requests that don't send a
            # browser-like User-Agent (Python's default urllib UA gets blocked).
            "User-Agent": "Mozilla/5.0 (LeadQualify-Automation)",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise SystemExit(f"dev.to API error {e.code}: {error_body}")
    except urllib.error.URLError as e:
        raise SystemExit(f"Network error calling dev.to API: {e.reason}")


def main():
    env = load_env()
    if not env["api_key"]:
        raise SystemExit(
            "ERROR: DEVTO_API_KEY not found. Add it to .env "
            "(Settings -> Extensions -> DEV API Keys on dev.to)."
        )

    print("Loading blog drafts...")
    drafts_data = load_drafts()
    blog_posts = drafts_data["blog_posts"]

    log = load_published_log()
    published_slugs = set(log.get("published_slugs", []))

    # Find the first draft not yet published
    next_post = None
    for post in blog_posts:
        slug = post["metadata"]["slug"]
        if slug not in published_slugs:
            next_post = post
            break

    if next_post is None:
        print("All current drafts have already been published to dev.to. "
              "Run blog_agent.py to generate new drafts, or nothing to do.")
        return

    meta = next_post["metadata"]
    mode = "LIVE" if env["auto_publish"] else "DRAFT (unpublished)"
    print(f"Publishing '{meta['title']}' to dev.to as {mode}...")

    result = publish_to_devto(next_post, env["api_key"], env["auto_publish"])

    published_slugs.add(meta["slug"])
    log["published_slugs"] = sorted(published_slugs)
    log.setdefault("history", []).append({
        "slug": meta["slug"],
        "title": meta["title"],
        "devto_url": result.get("url"),
        "devto_id": result.get("id"),
        "published_live": env["auto_publish"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    save_published_log(log)

    print(f"Success. dev.to article id: {result.get('id')}")
    print(f"URL: {result.get('url')}")
    if not env["auto_publish"]:
        print("Note: posted as an UNPUBLISHED DRAFT. Log into dev.to to review and hit Publish.")


if __name__ == "__main__":
    main()