#!/usr/bin/env python3
"""
pinterest_engine.py
Autonomous Pinterest Visual Syndicator & Traffic Engine for aviperera.com.
Syndicates newly published research and essays to Pinterest using the Pinterest API v5.
Supports both remote featured images and auto-generated branded editorial cards.
"""

import os
import sys
import json
import html
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

from card_generator import generate_svg_card
from image_watermarker import create_branded_pin, is_pillow_available

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PINTEREST_API_ENDPOINT = os.getenv("PINTEREST_API_ENDPOINT", "https://api.pinterest.com/v5/pins")
PINTEREST_SANDBOX_ENDPOINT = "https://api-sandbox.pinterest.com/v5/pins"
RSS_FEED_URL = "https://aviperera.com/feed/"
WP_POSTS_API = "https://aviperera.com/wp-json/wp/v2/posts?per_page=10&_fields=id,link,title,excerpt,jetpack_featured_media_url"
STATE_FILE = os.path.join(os.path.dirname(__file__), "state", "pinned_history.json")
CARDS_DIR = os.path.join(os.path.dirname(__file__), "generated_cards")

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, application/json, */*"
}

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "pinned" not in data:
                    data["pinned"] = {}
                return data
        except Exception as e:
            print(f"[!] Warning reading state ({e}). Starting clean.")
    return {"pinned": {}, "last_run": None}

def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def clean_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    clean = re.sub(r"<[^>]+>", " ", raw_html)
    clean = html.unescape(clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

def extract_image_from_content(content_html: str) -> str:
    """Extracts first high-resolution img src from post content if present."""
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content_html)
    if match:
        url = match.group(1).strip()
        if url.startswith("http://") or url.startswith("https://"):
            return url
    return ""

def generate_seo_filename(title: str, category: str = "", author: str = "Avi Perera", domain: str = "aviperera.com") -> str:
    """
    Generates high-authority, SEO/GEO-optimized image filenames.
    Pattern: avi-perera-[clean-topic-slug]-[category-tag]-dossier-aviperera-com
    Maximizes Google Images, Bing Visual Search, and Pinterest crawler ranking.
    """
    clean_author = re.sub(r"[^a-zA-Z0-9]+", "-", author.lower()).strip("-")
    clean_domain = re.sub(r"[^a-zA-Z0-9]+", "-", domain.lower()).strip("-")

    stop_words = {
        "a", "an", "the", "in", "on", "at", "by", "for", "with", "about",
        "against", "between", "into", "through", "during", "before", "after",
        "above", "below", "to", "from", "up", "down", "is", "are", "was",
        "were", "be", "been", "being", "have", "has", "had", "do", "does",
        "did", "and", "but", "if", "or", "because", "as", "until", "while",
        "what", "which", "who", "whom", "this", "that", "these", "those", "am"
    }

    title_words = re.findall(r"[a-zA-Z0-9]+", title.lower())
    meaningful_words = [w for w in title_words if w not in stop_words]
    if not meaningful_words:
        meaningful_words = title_words[:5]
    topic_slug = "-".join(meaningful_words[:6])

    cat_words = re.findall(r"[a-zA-Z0-9]+", category.lower())
    cat_slug = "-".join([w for w in cat_words if w not in stop_words][:3]) if cat_words else "ai-ethics"

    parts = [clean_author, topic_slug, cat_slug, "dossier", clean_domain]
    final_slug = "-".join([p for p in parts if p])
    final_slug = re.sub(r"-+", "-", final_slug).strip("-")
    return final_slug[:90]

def fetch_from_rss() -> List[Dict[str, Any]]:
    """Primary ingestion: Fetches posts and media enclosures from RSS feed (WAF-immune)."""
    try:
        req = urllib.request.Request(RSS_FEED_URL, headers=BROWSER_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw_xml = resp.read().decode("utf-8", errors="replace")
            clean_xml = re.sub(r"</?([a-zA-Z0-9_-]+):", lambda m: "</" if m.group(0).startswith("</") else "<", raw_xml)
            root = ET.fromstring(clean_xml)
            posts = []
            for item in root.findall(".//item"):
                guid_el = item.find("guid")
                title_el = item.find("title")
                link_el = item.find("link")
                desc_el = item.find("description")
                content_el = item.find("encoded")

                guid = guid_el.text.strip() if guid_el is not None and guid_el.text else ""
                title = clean_text(title_el.text) if title_el is not None and title_el.text else ""
                link = link_el.text.strip() if link_el is not None and link_el.text else ""
                desc = desc_el.text if desc_el is not None and desc_el.text else ""
                content = content_el.text if content_el is not None and content_el.text else ""
                excerpt = clean_text(desc if desc else content)[:300]

                # Extract category
                categories = []
                for cat in item.findall("category"):
                    if cat.text:
                        categories.append(clean_text(cat.text))
                primary_category = categories[0] if categories else "AI Ethics & Society"

                # Check for enclosure image or inline image
                image_url = ""
                enclosure = item.find("enclosure")
                if enclosure is not None:
                    enc_type = enclosure.get("type", "")
                    if "image" in enc_type:
                        image_url = enclosure.get("url", "").strip()

                if not image_url and content:
                    image_url = extract_image_from_content(content)

                post_id = guid if guid else link
                if title and link:
                    posts.append({
                        "id": post_id,
                        "title": title,
                        "link": link,
                        "excerpt": excerpt,
                        "category": primary_category,
                        "image_url": image_url
                    })
            return posts
    except Exception as e:
        print(f"[!] Primary RSS discovery notice: {e}")
        return []

def build_pinterest_payload(post: dict, board_id: str, image_url: str, image_base64: Optional[str] = None, content_type: str = "image/jpeg") -> dict:
    """Formats Pinterest API v5 payload with strict character constraints, UTM tracking, and base64 or URL media."""
    title = post["title"][:98]
    base_link = post["link"].split("?")[0].rstrip("/") + "/"
    utm_link = f"{base_link}?utm_source=pinterest&utm_medium=social&utm_campaign=syndication"
    
    category = post.get("category", "AI Ethics & Governance")
    excerpt = post.get("excerpt", "")
    
    description = (
        f"{title}\n\n"
        f"{excerpt}\n\n"
        f"Read full research dossier and legal breakdown on aviperera.com.\n\n"
        f"#{category.replace(' ', '')} #AIEthics #AIGovernance #TechPolicy #AviPerera"
    )[:495]

    if image_base64:
        media_source = {
            "source_type": "image_base64",
            "content_type": content_type,
            "data": image_base64
        }
    else:
        media_source = {
            "source_type": "image_url",
            "url": image_url
        }

    alt_text = f"Research dossier on {title} by Avi Perera on aviperera.com. Analysis covering {category} and tech policy."[:490]

    return {
        "link": utm_link,
        "title": title,
        "description": description,
        "alt_text": alt_text,
        "board_id": board_id,
        "media_source": media_source
    }

def post_pin(access_token: str, payload: dict) -> Tuple[bool, str]:
    """Posts a pin to Pinterest via REST API v5, handling token cleaning and sandbox fallback."""
    if not access_token:
        return False, "Access token not provided"

    clean_token = access_token.strip()
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token[7:].strip()

    headers = {
        "Authorization": f"Bearer {clean_token}",
        "Content-Type": "application/json",
        "User-Agent": "AviPinterestSyndicator/1.0"
    }

    data = json.dumps(payload).encode("utf-8")

    endpoints_to_try = [PINTEREST_API_ENDPOINT]
    if PINTEREST_API_ENDPOINT != PINTEREST_SANDBOX_ENDPOINT:
        endpoints_to_try.append(PINTEREST_SANDBOX_ENDPOINT)

    last_error = ""
    for ep in endpoints_to_try:
        req = urllib.request.Request(ep, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                pin_id = res_data.get("id", "created")
                print(f"[OK] Successfully created Pinterest Pin ({ep}): ID {pin_id}")
                return True, pin_id
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            last_error = f"HTTP {e.code} on {ep}: {err_msg}"
            print(f"[!] Pinterest API {last_error}")
            # If not 401 or if we reached the last endpoint, stop
            if e.code != 401:
                return False, last_error
        except Exception as e:
            last_error = str(e)
            print(f"[!] Request error on {ep}: {e}")

    return False, last_error

def main() -> int:
    print("=== Autonomous Pinterest Visual Syndicator & Traffic Engine ===")
    state = load_state()
    posts = fetch_from_rss()
    print(f"Retrieved {len(posts)} publications from aviperera.com")

    access_token = os.getenv("PINTEREST_ACCESS_TOKEN", "").strip()
    board_id = os.getenv("PINTEREST_BOARD_ID", "").strip()
    default_image_url = os.getenv("PINTEREST_DEFAULT_IMAGE_URL", "https://aviperera.com/wp-content/uploads/2024/09/Avi-Perera-website-aviperera.com-logo-welcome-to-my-website-friends-why-did-you-download-this-logo.png").strip()

    force_dry_run = "--dry-run" in sys.argv
    has_credentials = bool(access_token and board_id)
    dry_run = force_dry_run or not has_credentials

    if dry_run:
        print("[!] Running in PREVIEW / DRY-RUN mode.")
        if not has_credentials:
            print("    Reason: Missing PINTEREST_ACCESS_TOKEN or PINTEREST_BOARD_ID repository secrets.")

    # Find unpinned posts
    unpinned = [p for p in posts if p["id"] not in state["pinned"] and p["link"] not in state["pinned"]]
    print(f"Publications pending Pinterest syndication: {len(unpinned)}")

    # Process 1 post per run to maintain high-quality pacing
    processed_items = []
    os.makedirs(CARDS_DIR, exist_ok=True)

    for post in unpinned[:1]:
        title = post["title"]
        pid = post["id"]
        category = post.get("category", "AI Ethics & Society")
        excerpt = post.get("excerpt", "")
        
        # 1. Determine base image
        image_url = post.get("image_url")
        if not image_url:
            image_url = default_image_url

        # High-Authority SEO/GEO filename: avi-perera-[topic]-[category]-dossier-aviperera-com
        seo_basename = generate_seo_filename(title=title, category=category)

        # 2. Try creating branded 1000x1500 composite image with Avi Perera's logo and aviperera.com watermark
        jpg_card_path = os.path.join(CARDS_DIR, f"{seo_basename}.jpg")
        image_base64, content_type = create_branded_pin(
            title=title,
            image_url=image_url,
            category=category,
            excerpt=excerpt,
            output_path=jpg_card_path
        )
        if image_base64:
            print(f"[OK] Generated branded composite pin with logo & watermark: {jpg_card_path}")

        # 3. Also generate local branded SVG card for vector preservation
        svg_content = generate_svg_card(
            title=title,
            category=category,
            excerpt=excerpt
        )
        svg_card_path = os.path.join(CARDS_DIR, f"{seo_basename}.svg")
        with open(svg_card_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

        payload = build_pinterest_payload(
            post,
            board_id=board_id or "DEMO_BOARD_ID",
            image_url=image_url,
            image_base64=image_base64,
            content_type=content_type or "image/jpeg"
        )

        item_summary = {
            "title": title,
            "link": payload["link"],
            "image": image_url,
            "status": "Dry-Run Preview"
        }

        if dry_run:
            print(f"\n[DRY-RUN PIN PREVIEW]")
            print(f"Title: {payload['title']}")
            print(f"Link: {payload['link']}")
            print(f"Image: {image_url}")
            print(f"Description:\n{payload['description']}")
            processed_items.append(item_summary)
            continue

        # Live Submission
        success, pin_id = post_pin(access_token, payload)
        if success:
            state["pinned"][pid] = {
                "title": title,
                "link": post["link"],
                "pin_id": pin_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            state["last_run"] = datetime.now(timezone.utc).isoformat()
            save_state(state)
            item_summary["status"] = f"Pinned ({pin_id})"
            processed_items.append(item_summary)
        else:
            item_summary["status"] = "Failed"
            processed_items.append(item_summary)

    output_step_summary(processed_items, dry_run=dry_run, has_credentials=has_credentials)
    return 0

def output_step_summary(items: list, dry_run: bool, has_credentials: bool):
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    with open(summary_path, "a", encoding="utf-8") as f:
        f.write("## 📌 Pinterest Visual Syndicator & Traffic Engine\n\n")
        mode_badge = "🟡 *DRY-RUN / PREVIEW*" if dry_run else "🟢 *LIVE PIN CREATION SUCCESS*"
        f.write(f"**Execution Mode:** {mode_badge}\n\n")
        f.write(f"- **Pinterest Credentials:** {'✅ Configured' if has_credentials else '❌ Missing PINTEREST_ACCESS_TOKEN or PINTEREST_BOARD_ID'}\n\n")

        if not items:
            f.write("✅ All recent publications are already pinned. Zero pending items.\n")
            return

        f.write(f"### Processed Publication ({len(items)} item):\n\n")
        f.write("| Title | Target Link | Status |\n")
        f.write("| :--- | :--- | :--- |\n")
        for it in items:
            f.write(f"| {it['title']} | [{it['link']}]({it['link']}) | `{it['status']}` |\n")

if __name__ == "__main__":
    sys.exit(main())

