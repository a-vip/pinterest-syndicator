import os
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock

from card_generator import generate_svg_card
from pinterest_engine import (
    clean_text,
    extract_image_from_content,
    build_pinterest_payload,
    generate_seo_filename,
    load_state,
    save_state
)

class TestPinterestSyndicator(unittest.TestCase):

    def test_clean_text(self):
        raw = "<p>Test <strong>bold</strong> &amp; clean</p>"
        cleaned = clean_text(raw)
        self.assertEqual(cleaned, "Test bold & clean")

    def test_generate_seo_filename(self):
        title = "Has Trump Become a Dictator? What the Evidence Shows"
        cat = "Governance & Politics"
        filename = generate_seo_filename(title, category=cat, author="Avi Perera", domain="aviperera.com")
        self.assertTrue(filename.startswith("avi-perera-"))
        self.assertIn("trump", filename)
        self.assertIn("dictator", filename)
        self.assertIn("evidence", filename)
        self.assertIn("governance", filename)
        self.assertIn("aviperera-com", filename)
        self.assertLessEqual(len(filename), 95)
        self.assertNotIn(" ", filename)
        self.assertNotIn("_", filename)

    def test_extract_image_from_content(self):
        html_with_img = '<p>Some intro</p><img src="https://aviperera.com/wp-content/uploads/sample.jpg" alt="test" />'
        img_url = extract_image_from_content(html_with_img)
        self.assertEqual(img_url, "https://aviperera.com/wp-content/uploads/sample.jpg")

        no_img = '<p>No image here</p>'
        self.assertEqual(extract_image_from_content(no_img), "")

    def test_build_pinterest_payload(self):
        post = {
            "title": "A " * 60,  # 120 chars
            "link": "https://aviperera.com/ai-ethics-and-legal-liability/",
            "category": "AI Ethics",
            "excerpt": "Exploring algorithmic governance, human rights, and legal liability."
        }
        board_id = "test_board_123"
        image_url = "https://aviperera.com/sample.jpg"

        payload = build_pinterest_payload(post, board_id=board_id, image_url=image_url)

        self.assertLessEqual(len(payload["title"]), 100)
        self.assertLessEqual(len(payload["description"]), 500)
        self.assertEqual(payload["board_id"], "test_board_123")
        self.assertIn("utm_source=pinterest", payload["link"])
        self.assertEqual(payload["media_source"]["url"], image_url)

        # Test base64 payload branch
        payload_b64 = build_pinterest_payload(
            post,
            board_id=board_id,
            image_url=image_url,
            image_base64="aGVsbG8=",
            content_type="image/jpeg"
        )
        self.assertEqual(payload_b64["media_source"]["source_type"], "image_base64")
        self.assertEqual(payload_b64["media_source"]["data"], "aGVsbG8=")
        self.assertEqual(payload_b64["media_source"]["content_type"], "image/jpeg")

    def test_generate_svg_card(self):
        svg = generate_svg_card(
            title="The Future of Autonomous AI Systems & Accountability",
            category="AI Ethics & Governance",
            excerpt="Analyzing democratic oversight, legal liability, and international norms.",
            author="Avi Perera",
            domain="aviperera.com"
        )
        self.assertTrue(svg.startswith("<svg"))
        self.assertTrue(svg.strip().endswith("</svg>"))
        self.assertIn("AI ETHICS &amp; GOVERNANCE", svg)
        self.assertIn("AVIPERERA.COM", svg)
        self.assertIn("Avi Perera", svg)

    def test_load_and_save_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_state_file = os.path.join(tmpdir, "state", "pinned_history.json")
            with patch("pinterest_engine.STATE_FILE", test_state_file):
                state = load_state()
                self.assertEqual(state["pinned"], {})
                
                state["pinned"]["post-123"] = {
                    "title": "Sample Post",
                    "link": "https://aviperera.com/sample",
                    "pin_id": "pin987"
                }
                save_state(state)
                
                reloaded = load_state()
                self.assertIn("post-123", reloaded["pinned"])
                self.assertEqual(reloaded["pinned"]["post-123"]["pin_id"], "pin987")

if __name__ == "__main__":
    unittest.main()

