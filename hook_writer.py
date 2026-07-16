"""
Agent 2: Hook & Script Writer
------------------------------
Reads competitor themes from Agent 1, generates 5 content hooks as Faria.
Writes natively for LinkedIn, Instagram, Blog.

Uses Google Gemini API (free tier).

Run:
    python hook_writer.py
"""

import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import urllib.request
import urllib.parse

load_dotenv()

IDEATOR_SUMMARY = "data/ideator_summary.json"
OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Google Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise SystemExit("ERROR: GOOGLE_API_KEY not found in .env")

GEMINI_MODEL = "gemini-3.5-flash"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GOOGLE_API_KEY}"


def load_themes():
    """Load top themes from ideator output."""
    if not os.path.exists(IDEATOR_SUMMARY):
        raise SystemExit(f"ERROR: {IDEATOR_SUMMARY} not found. Run ideator.py first.")
    with open(IDEATOR_SUMMARY, encoding='utf-8') as f:
        return json.load(f)


def generate_hooks(themes):
    """Generate 5 content hooks as Faria using Google Gemini."""
    
    top_themes = [t['theme'] for t in themes['top_themes'][:3]]
    themes_str = ", ".join(top_themes)
    
    prompt = f"""You are Faria Raghib, founder of LeadQualify (a B2B lead scoring AI platform).

Your voice is: direct, technical, founder-first. No marketing fluff. You call out real problems.
You target: sales teams, revenue ops, SDRs at mid-market/enterprise.

Competitor themes that are working: {themes_str}

Your product: LeadQualify scores leads using AI to identify which ones are actually worth pursuing.

Generate exactly 5 content ideas (hooks), with this EXACT platform distribution (non-negotiable):
- 2 hooks for "linkedin"
- 2 hooks for "instagram"
- 1 hook for "blog"

Each hook should:
1. Own the lead-scoring space vs competitors
2. Be written natively for its platform (LinkedIn = professional/analytical, Instagram = punchy/visual-first caption, Blog = educational headline-style)
3. Have a spicy/honest take (like the "roast" strategy)
4. Tie to LeadQualify's value

Format your response ONLY as valid JSON with this exact structure:
{{
  "hooks": [
    {{
      "platform": "linkedin",
      "hook": "Short punchy hook (under 280 chars for social)",
      "angle": "What problem does this solve?",
      "cta": "What's the ask? (read more, try free, etc)"
    }}
  ]
}}

Generate exactly 5 hooks. Make them sound like Faria wrote them. Direct. Specific. Not salesy.
Output ONLY the JSON, no other text."""

    url = GEMINI_API_URL
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2000,
            "responseMimeType": "application/json"
        }
    }
    
    print("Generating hooks as Faria (via Google Gemini)...")
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        # Extract text from Gemini response
        content = result['candidates'][0]['content']['parts'][0]['text']

        # With responseMimeType set, Gemini's output IS the JSON directly -
        # no need to regex-extract it from surrounding text.
        try:
            hooks_data = json.loads(content)
            return hooks_data['hooks']
        except json.JSONDecodeError:
            # Fallback: try to extract a {...} block in case there's any wrapping text
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                hooks_data = json.loads(json_match.group())
                return hooks_data['hooks']
            print(f"Raw response: {content}")
            raise ValueError("Could not parse JSON from Gemini response")
            
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        raise


def main():
    print("Loading competitor themes...")
    themes = load_themes()
    
    print(f"Top themes: {[t['theme'] for t in themes['top_themes'][:3]]}")
    
    hooks = generate_hooks(themes)
    
    # Save hooks
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "themes_analyzed": [t['theme'] for t in themes['top_themes']],
        "hooks": hooks
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