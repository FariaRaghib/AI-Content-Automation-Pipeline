"""
Agent 2: Hook & Script Writer (MOCK VERSION)
---------------------------------------------
Generates 5 sample content hooks as Faria without API calls.
Use this to test the full pipeline while we fix the API integration.

Run:
    python hook_writer_mock.py
"""

import os
import json
from datetime import datetime, timezone

IDEATOR_SUMMARY = "data/ideator_summary.json"
OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_themes():
    """Load top themes from ideator output."""
    if not os.path.exists(IDEATOR_SUMMARY):
        raise SystemExit(f"ERROR: {IDEATOR_SUMMARY} not found. Run ideator.py first.")
    with open(IDEATOR_SUMMARY, encoding='utf-8') as f:
        return json.load(f)


def generate_sample_hooks():
    """Generate 5 sample hooks as Faria (hardcoded for testing)."""
    return [
        {
            "platform": "linkedin",
            "hook": "Your lead scoring is wrong. You're optimizing for the lead, not for whether they'll actually close. LeadQualify scores for buying intent, not just fit.",
            "angle": "Expose the flaw in competitor scoring models",
            "cta": "See how we do it differently (free trial)"
        },
        {
            "platform": "linkedin",
            "hook": "87% of leads never close. Most tools score them the same way. We identify the 13% that matter before your team wastes time.",
            "angle": "Lead quality > lead quantity",
            "cta": "Try our lead roast (free, brutal, honest)"
        },
        {
            "platform": "instagram",
            "hook": "Your CRM is a graveyard of dead leads. LeadQualify revives it—AI scores what's actually worth pursuing.",
            "angle": "Raw, direct call-out of wasted pipeline",
            "cta": "See which leads are worth your time"
        },
        {
            "platform": "blog",
            "hook": "Why Your Lead Scoring Model Fails (And How Ours Doesn't)",
            "angle": "Educational + SEO: teach readers the gaps in their current approach",
            "cta": "Read the full breakdown + checklist"
        },
        {
            "platform": "linkedin",
            "hook": "Multi-channel outreach doesn't work if you're reaching the wrong people first. LeadQualify + your sales stack = qualified pipeline at scale.",
            "angle": "Orchestration starts with who you score",
            "cta": "See the integration (3 min demo)"
        }
    ]


def main():
    print("Loading competitor themes...")
    themes = load_themes()
    
    print(f"Top themes: {[t['theme'] for t in themes['top_themes'][:3]]}")
    
    print("Generating sample hooks as Faria (mock version)...")
    hooks = generate_sample_hooks()
    
    # Save hooks
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "themes_analyzed": [t['theme'] for t in themes['top_themes']],
        "hooks": hooks,
        "note": "MOCK VERSION - Replace with real API calls when Gemini API is working"
    }
    
    hooks_path = os.path.join(OUTPUT_DIR, "hook_writer_output.json")
    with open(hooks_path, "w", encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved hooks -> {hooks_path}\n")
    
    # Print for review
    print("--- 5 CONTENT HOOKS (As Faria) ---\n")
    for i, hook in enumerate(hooks, 1):
        print(f"{i}. [{hook['platform'].upper()}]")
        print(f"   Hook: {hook['hook']}")
        print(f"   Angle: {hook['angle']}")
        print(f"   CTA: {hook['cta']}")
        print()


if __name__ == "__main__":
    main()