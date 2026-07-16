"""
Image Generator: Branded Quote Cards
--------------------------------------
Creates a simple, clean text-card image from a hook, styled for LeadQualify.
Used as the required image for Instagram posts (Instagram can't post text-only).

Run standalone to test:
    python image_generator.py
"""

import os
from PIL import Image, ImageDraw, ImageFont
import textwrap

OUTPUT_DIR = "data/images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Simple brand colors - adjust to match LeadQualify's actual brand later
BG_COLOR = (17, 24, 39)       # dark navy/charcoal
TEXT_COLOR = (255, 255, 255)  # white
ACCENT_COLOR = (99, 179, 237) # light blue accent

WIDTH, HEIGHT = 1080, 1080  # Instagram square format


def get_font(size):
    """Try to load a clean font, fall back to default if not available."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "C:\\Windows\\Fonts\\Arial.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def generate_quote_card(hook_text, filename="quote_card.png"):
    """Generate a square branded image with the hook text centered."""

    img = Image.new("RGB", (WIDTH, HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Wrap text to fit width
    font_size = 64
    font = get_font(font_size)

    max_chars_per_line = 24
    wrapped = textwrap.fill(hook_text, width=max_chars_per_line)
    lines = wrapped.split("\n")

    # Shrink font if too many lines (keeps text on-card)
    while len(lines) > 8 and font_size > 32:
        font_size -= 4
        font = get_font(font_size)
        max_chars_per_line += 2
        wrapped = textwrap.fill(hook_text, width=max_chars_per_line)
        lines = wrapped.split("\n")

    # Calculate total text block height to center vertically
    line_height = font_size + 16
    total_height = line_height * len(lines)
    start_y = (HEIGHT - total_height) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        x = (WIDTH - line_width) // 2
        y = start_y + (i * line_height)
        draw.text((x, y), line, font=font, fill=TEXT_COLOR)

    # Brand tag at bottom
    brand_font = get_font(36)
    brand_text = "LeadQualify"
    bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
    brand_width = bbox[2] - bbox[0]
    draw.text(
        ((WIDTH - brand_width) // 2, HEIGHT - 100),
        brand_text,
        font=brand_font,
        fill=ACCENT_COLOR
    )

    # Accent line above brand tag
    draw.line(
        [(WIDTH // 2 - 40, HEIGHT - 130), (WIDTH // 2 + 40, HEIGHT - 130)],
        fill=ACCENT_COLOR,
        width=4
    )

    filepath = os.path.join(OUTPUT_DIR, filename)
    img.save(filepath, "PNG")
    return filepath


if __name__ == "__main__":
    test_hook = "Your CRM is a graveyard of dead leads. LeadQualify revives it."
    path = generate_quote_card(test_hook, "test_card.png")
    print(f"[OK] Generated test image: {path}")
