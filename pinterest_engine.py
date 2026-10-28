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

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PINTEREST_API_ENDPOINT = "https://api.pinterest.com/v5/pins"
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

def build_pinterest_payload(post: dict, board_id: str, image_url: str) -> dict:
    """Formats Pinterest API v5 payload with strict character constraints and UTM tracking."""
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

    return {
        "link": utm_link,
        "title": title,
        "description": description,
        "board_id": board_id,
        "media_source": {
            "source_type": "image_url",
            "url": image_url
        }
    }

def post_pin(access_token: str, payload: dict) -> Tuple[bool, str]:
    """Posts a pin to Pinterest via REST API v5."""
    if not access_token:
        return False, "Access token not provided"
        
    headers = {
        "Authorization": f"Bearer {access_token.strip()}",
        "Content-Type": "application/json",
        "User-Agent": "AviPinterestSyndicator/1.0"
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(PINTEREST_API_ENDPOINT, data=data, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            pin_id = res_data.get("id", "created")
            print(f"[OK] Successfully created Pinterest Pin: ID {pin_id}")
            return True, pin_id
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        print(f"[!] Pinterest API HTTP Error {e.code}: {err_msg}")
        return False, err_msg
    except Exception as e:
        print(f"[!] Failed to post Pin: {e}")
        return False, str(e)

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
        
        # 1. Determine image: use article featured image, or generate clean branded SVG card
        image_url = post.get("image_url")
        if not image_url:
            image_url = default_image_url
            
        # Also generate local branded card for consistency
        svg_content = generate_svg_card(
            title=title,
            category=category,
            excerpt=excerpt
        )
        safe_filename = re.sub(r"[^a-zA-Z0-9_-]", "_", title)[:50] + ".svg"
        card_path = os.path.join(CARDS_DIR, safe_filename)
        with open(card_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        print(f"[OK] Generated branded card: {card_path}")

        payload = build_pinterest_payload(post, board_id=board_id or "DEMO_BOARD_ID", image_url=image_url)

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
