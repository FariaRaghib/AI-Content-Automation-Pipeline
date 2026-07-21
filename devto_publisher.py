"""
Agent 7: Dev.to Publisher (+ post status tracking)
-------------------------------------------------------
Takes blog drafts from blog_agent.py (data/blog_agent_drafts.json)
and publishes them to dev.to via their REST API.

Keeps a log (data/devto_published_log.json) of what's already been
published so re-running this script doesn't create duplicate posts.

NEW: writes a status record to data/post_status.json after every run -
whether it posted successfully (live or as a draft), failed, or was
skipped (nothing new to publish) - so telegram_bot_fixed.py can report
"posted / failed / skipped" per platform in the daily digest.

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
STATUS_FILE = os.path.join(DATA_DIR, "post_status.json")

DEVTO_API_URL = "https://dev.to/api/articles"


# =========================================================
# Status tracking (shared across all platform publishers)
# =========================================================
def write_status(platform, status, detail=None, post_id=None):
    """
    Update this platform's entry in the shared post_status.json file,
    without touching other platforms' entries.

    status: "posted" | "failed" | "skipped"
    detail: error message (for "failed") or a short note (for "skipped"/"posted")
    """
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)

    all_status = {}
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, encoding='utf-8') as f:
                all_status = json.load(f)
        except (json.JSONDecodeError, OSError):
            all_status = {}  # if the file's corrupted, don't crash - just start fresh

    all_status[platform] = {
        "status": status,
        "detail": detail,
        "post_id": post_id,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    with open(STATUS_FILE, "w", encoding='utf-8') as f:
        json.dump(all_status, f, indent=2, ensure_ascii=False)


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
        raise Exception(f"dev.to API error {e.code}: {error_body}")
    except urllib.error.URLError as e:
        raise Exception(f"Network error calling dev.to API: {e.reason}")


def main():
    env = load_env()
    if not env["api_key"]:
        msg = ("DEVTO_API_KEY not found. Add it to .env "
               "(Settings -> Extensions -> DEV API Keys on dev.to).")
        print(f"ERROR: {msg}")
        write_status("blog", "failed", detail=msg)
        raise SystemExit(f"ERROR: {msg}")

    try:
        print("Loading blog drafts...")
        drafts_data = load_drafts()
    except SystemExit as e:
        write_status("blog", "failed", detail=str(e))
        raise

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
        msg = "All current drafts have already been published to dev.to."
        print(f"{msg} Run blog_agent.py to generate new drafts, or nothing to do.")
        write_status("blog", "skipped", detail=msg)
        return

    meta = next_post["metadata"]
    mode = "LIVE" if env["auto_publish"] else "DRAFT (unpublished)"
    print(f"Publishing '{meta['title']}' to dev.to as {mode}...")

    try:
        result = publish_to_devto(next_post, env["api_key"], env["auto_publish"])
    except Exception as e:
        print(f"[FAIL] dev.to publish failed: {e}")
        write_status("blog", "failed", detail=str(e))
        raise

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

    status_detail = f"{meta['title'][:80]} ({mode.lower()})"
    write_status("blog", "posted", detail=status_detail, post_id=result.get("id"))


if __name__ == "__main__":
    main()