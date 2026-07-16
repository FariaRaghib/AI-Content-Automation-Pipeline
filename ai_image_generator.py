"""
AI Image Generator (Gemini / Nano Banana)
--------------------------------------------
Generates a real illustration/photo-style image based on the post's content,
using Google's Gemini image generation model (gemini-2.5-flash-image).

This uses the SAME GOOGLE_API_KEY already set up for hook_writer.py.
Google AI Studio provides a free daily quota for this without requiring
a credit card - if that runs out or requires billing, this will raise
a clear error so we know to fall back to the quote-card generator instead.

Run standalone to test:
    python ai_image_generator.py
"""

import os
import json
import base64
from dotenv import load_dotenv
import urllib.request

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise SystemExit("ERROR: GOOGLE_API_KEY not found in .env")

IMAGE_MODEL = "gemini-2.5-flash-image"
IMAGE_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{IMAGE_MODEL}:generateContent?key={GOOGLE_API_KEY}"

OUTPUT_DIR = "data/images"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_ai_image(hook_text, filename="ai_generated.png"):
    """
    Generate a real illustration based on the hook's topic.
    Builds a descriptive visual prompt from the hook text (not the literal
    hook words as text-in-image - a clean scene/illustration instead).
    """
    visual_prompt = (
        f"A clean, professional, modern flat-illustration style image for a B2B SaaS "
        f"social media post. Theme: {hook_text}. "
        f"Style: minimalist corporate illustration, navy blue and gold color palette, "
        f"no text or words in the image, high quality, professional, tech/sales themed."
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": visual_prompt}
                ]
            }
        ]
    }

    req = urllib.request.Request(
        IMAGE_API_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req, timeout=60) as response:
        result = json.loads(response.read().decode('utf-8'))

    # Find the image data in the response parts
    parts = result['candidates'][0]['content']['parts']
    image_data = None
    for part in parts:
        if 'inlineData' in part:
            image_data = part['inlineData']['data']
            break

    if not image_data:
        raise Exception(f"No image returned in response: {result}")

    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(base64.b64decode(image_data))

    return filepath


if __name__ == "__main__":
    import urllib.error
    test_hook = "Your CRM is a graveyard of dead leads. LeadQualify revives it."
    try:
        path = generate_ai_image(test_hook, "test_ai_image.png")
        print(f"[OK] Generated AI image: {path}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"[FAIL] HTTP Error {e.code}: {e.reason}")
        print(f"Details: {error_body}")
    except Exception as e:
        print(f"[FAIL] {e}")
        print("\nIf this mentions billing/quota, the free tier isn't available for your account.")
        print("Fallback: use image_generator.py (branded quote-card, unlimited free) instead.")