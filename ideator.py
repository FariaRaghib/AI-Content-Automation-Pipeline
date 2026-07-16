"""
Agent 1: Ideator
-----------------
Reads curated competitor posts from competitors.json,
summarizes engagement patterns and content themes.

Run:
    python ideator.py
"""

import os
import json
from datetime import datetime, timezone

OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)
COMPETITORS_FILE = "competitors.json"


def load_competitors():
    """Load curated competitor posts from competitors.json."""
    if not os.path.exists(COMPETITORS_FILE):
        raise SystemExit(
            f"ERROR: {COMPETITORS_FILE} not found.\n"
            "Create it with the template from competitors.json.example"
        )
    with open(COMPETITORS_FILE, encoding='utf-8') as f:
        return json.load(f)


def analyze_posts(posts):
    """Analyze posts for themes and patterns."""
    # Group by platform
    by_platform = {}
    for p in posts:
        platform = p.get("platform", "unknown")
        if platform not in by_platform:
            by_platform[platform] = []
        by_platform[platform].append(p)
    
    # Extract themes
    themes = {}
    for p in posts:
        tags = p.get("tags", [])
        for tag in tags:
            themes[tag] = themes.get(tag, 0) + 1
    
    # Sort themes by frequency
    top_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "by_platform": {k: len(v) for k, v in by_platform.items()},
        "top_themes": [{"theme": t, "count": c} for t, c in top_themes],
        "posts_analyzed": len(posts),
    }


def main():
    print("Loading competitor data...")
    posts = load_competitors()
    
    # Save raw
    raw_path = os.path.join(OUTPUT_DIR, "raw_competitor_data.json")
    with open(raw_path, "w", encoding='utf-8') as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved raw data -> {raw_path}")
    
    # Analyze
    analysis = analyze_posts(posts)
    analysis["generated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Save summary
    summary_path = os.path.join(OUTPUT_DIR, "ideator_summary.json")
    with open(summary_path, "w", encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved analysis -> {summary_path}")
    
    # Print top themes
    print("\n--- COMPETITOR CONTENT PATTERNS ---")
    print(f"Posts analyzed: {analysis['posts_analyzed']}")
    print(f"Platforms: {analysis['by_platform']}")
    print("\nTop themes:")
    for theme_info in analysis["top_themes"]:
        print(f"  • {theme_info['theme']}: {theme_info['count']} posts")


if __name__ == "__main__":
    main()