#!/usr/bin/env python3
"""
image_watermarker.py
Autonomous Image Watermarker & Editorial Pin Synthesizer for Pinterest.
Embeds Avi Perera's official logo, custom typography, and aviperera.com watermark
onto 1000x1500 (2:3) Pinterest visual assets.
"""

import os
import io
import re
import html
import base64
import textwrap
import urllib.request
from typing import Optional, Tuple

LOGO_FILE = os.path.join(os.path.dirname(__file__), "assets", "logo.png")

# Fallback default font and colors
BG_TOP = (11, 15, 25)       # #0B0F19
BG_BOTTOM = (31, 41, 55)    # #1F2937
CARD_BG = (15, 23, 42)      # #0F172A
TEXT_WHITE = (248, 250, 252) # #F8FAFC
TEXT_MUTED = (148, 163, 184) # #94A3B8
ACCENT_BLUE = (56, 189, 248) # #38BDF8
BORDER_COLOR = (51, 65, 85) # #334155

def is_pillow_available() -> bool:
    try:
        import PIL
        return True
    except ImportError:
        return False

def create_branded_pin(
    title: str,
    image_url: Optional[str] = None,
    category: str = "AI ETHICS & SOCIETY",
    excerpt: str = "",
    author: str = "Avi Perera",
    domain: str = "aviperera.com",
    output_path: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Creates a 1000x1500 branded pin image with article image, logo, and aviperera.com watermark.
    Returns: (base64_data_string, content_type) e.g. ("...", "image/jpeg")
    """
    if not is_pillow_available():
        print("[i] Pillow not available in current environment; skipping raster compositing.")
        return None, None

    from PIL import Image, ImageDraw, ImageFont, ImageFilter

    WIDTH = 1000
    HEIGHT = 1500

    # 1. Create Base Vertical Canvas (1000x1500) with vertical dark gradient
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), BG_TOP)
    draw = ImageDraw.Draw(canvas)

    # Vertical gradient interpolation
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(BG_TOP[0] * (1 - ratio) + BG_BOTTOM[0] * ratio)
        g = int(BG_TOP[1] * (1 - ratio) + BG_BOTTOM[1] * ratio)
        b = int(BG_TOP[2] * (1 - ratio) + BG_BOTTOM[2] * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b, 255))

    # Border frame
    draw.rounded_rectangle([40, 40, WIDTH - 40, HEIGHT - 40], radius=24, outline=BORDER_COLOR, width=2)

    # Load Fonts (Use standard system TrueType if available, or default PIL font)
    try:
        font_large = ImageFont.truetype("arialbd.ttf", 46)
        font_med = ImageFont.truetype("arial.ttf", 24)
        font_badge = ImageFont.truetype("arialbd.ttf", 20)
        font_watermark = ImageFont.truetype("arialbd.ttf", 26)
        font_author = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
            font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
            font_badge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
            font_watermark = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            font_author = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except Exception:
            font_large = ImageFont.load_default()
            font_med = ImageFont.load_default()
            font_badge = ImageFont.load_default()
            font_watermark = ImageFont.load_default()
            font_author = ImageFont.load_default()

    # 2. Header: Logo + Category Badge
    # Try loading local logo
    if os.path.exists(LOGO_FILE):
        try:
            logo = Image.open(LOGO_FILE).convert("RGBA")
            logo.thumbnail((70, 70), Image.Resampling.LANCZOS)
            canvas.paste(logo, (70, 70), logo)
        except Exception as e:
            print(f"[!] Notice: Logo load error ({e})")

    # Category Badge Pill
    badge_text = category.upper()
    pill_w = max(240, len(badge_text) * 14 + 40)
    pill_x1 = (WIDTH // 2) - (pill_w // 2)
    pill_y1 = 80
    pill_x2 = pill_x1 + pill_w
    pill_y2 = pill_y1 + 44
    draw.rounded_rectangle([pill_x1, pill_y1, pill_x2, pill_y2], radius=22, fill=(30, 41, 59, 220), outline=ACCENT_BLUE, width=1)
    draw.text(((pill_x1 + pill_x2) // 2, pill_y1 + 10), badge_text, font=font_badge, fill=ACCENT_BLUE, anchor="mt")

    # 3. Featured Image Mounting (Middle Frame)
    img_mounted = False
    if image_url:
        try:
            req = urllib.request.Request(
                image_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                art_img = Image.open(io.BytesIO(resp.read())).convert("RGBA")
                
                # Fit into 860 x 620 container
                box_w = 860
                box_h = 620
                art_img.thumbnail((box_w, box_h), Image.Resampling.LANCZOS)
                
                img_x = (WIDTH - art_img.width) // 2
                img_y = 170 + ((box_h - art_img.height) // 2)
                
                # Draw subtle background panel
                draw.rounded_rectangle([60, 160, WIDTH - 60, 160 + box_h + 20], radius=16, fill=(15, 23, 42, 230), outline=BORDER_COLOR, width=1)
                canvas.paste(art_img, (img_x, img_y), art_img)
                img_mounted = True
        except Exception as e:
            print(f"[!] Notice: Could not download/mount article image ({e})")

    # 4. Text & Title Enclosure
    text_start_y = 840 if img_mounted else 360
    card_h = 440 if img_mounted else 820
    draw.rounded_rectangle([60, text_start_y, WIDTH - 60, text_start_y + card_h], radius=16, fill=(15, 23, 42, 230), outline=BORDER_COLOR, width=1)

    # Accent divider line
    draw.line([(WIDTH // 2 - 60, text_start_y + 30), (WIDTH // 2 + 60, text_start_y + 30)], fill=ACCENT_BLUE, width=4)

    # Wrap title
    clean_title = html.unescape(title.strip())
    wrapped_title = textwrap.wrap(clean_title, width=32)[:3]
    cur_y = text_start_y + 60
    for line in wrapped_title:
        draw.text((WIDTH // 2, cur_y), line, font=font_large, fill=TEXT_WHITE, anchor="mt")
        cur_y += 58

    # Wrap excerpt
    if excerpt:
        clean_excerpt = html.unescape(excerpt.strip()[:160])
        if not clean_excerpt.endswith("."):
            clean_excerpt += "..."
        wrapped_excerpt = textwrap.wrap(clean_excerpt, width=48)[:3]
        cur_y += 15
        for eline in wrapped_excerpt:
            draw.text((WIDTH // 2, cur_y), eline, font=font_med, fill=TEXT_MUTED, anchor="mt")
            cur_y += 34

    # 5. Prominent Watermark & Footer Anchor (URL & Brand)
    footer_y = HEIGHT - 150
    # CTA Pill
    cta_w = 340
    cta_h = 50
    cta_x1 = (WIDTH // 2) - (cta_w // 2)
    cta_y1 = footer_y - 25
    draw.rounded_rectangle([cta_x1, cta_y1, cta_x1 + cta_w, cta_y1 + cta_h], radius=25, fill=ACCENT_BLUE)
    draw.text((WIDTH // 2, cta_y1 + 12), "READ DOSSIER →", font=font_badge, fill=BG_TOP, anchor="mt")

    # Watermark Domain & Author Attribution
    domain_watermark = f"WWW.{domain.upper()}"
    draw.text((WIDTH // 2, footer_y + 40), domain_watermark, font=font_watermark, fill=TEXT_WHITE, anchor="mt")
    draw.text((WIDTH // 2, footer_y + 75), f"Official Research & Analysis by {author}", font=font_author, fill=TEXT_MUTED, anchor="mt")

    # 6. Export as RGB JPEG
    rgb_canvas = canvas.convert("RGB")
    buf = io.BytesIO()
    rgb_canvas.save(buf, format="JPEG", quality=92, optimize=True)
    jpeg_bytes = buf.getvalue()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(jpeg_bytes)

    b64_str = base64.b64encode(jpeg_bytes).decode("utf-8")
    return b64_str, "image/jpeg"
