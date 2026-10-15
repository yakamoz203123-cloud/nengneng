import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from render_social import render_social_page


def valid_layout_design(profile="xiaohongshu-feed-3x4"):
    if profile == "xiaohongshu-feed-3x4":
        canvas = {"width_px": 1080, "height_px": 1440}
        source_aspect_ratio = "3:4"
    else:
        canvas = {"width_px": 1080, "height_px": 1920}
        source_aspect_ratio = "9:16"
    return {
        "layout_style_version": "layout-v1",
        "layout_mode": "soft-card",
        "text_anchor": "bottom-left",
        "text_treatment": "soft-card",
        "text_align": "left",
        "max_lines": 4,
        "focal_point": "孩子手中的纸飞机",
        "text_safe_area": "画面下方的浅色地面",
        "avoid_covering": ["人物脸部", "纸飞机"],
        "page_rhythm": "action",
        "palette_token": "warm-paper",
        "status": "passed",
        "social_layout": {
            "profile": profile,
            "canvas": canvas,
            "subject_safe_area": [0.08, 0.10, 0.84, 0.62],
            "text_safe_area": [0.08, 0.76, 0.84, 0.14],
            "avoid_regions": ["top-ui", "bottom-ui"],
            "source_aspect_ratio": source_aspect_ratio,
            "status": "passed",
        },
    }


class SocialRenderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "social-source.png"
        Image.new("RGB", (900, 1200), (120, 160, 200)).save(self.source)
        self.page = {
            "image_path": self.source,
            "text": "小朋友一起造桥。",
            "font_path": ROOT / "assets" / "kidsbook-print.ttf",
            "layout_design": valid_layout_design(),
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_social_renderer_defaults_to_xiaohongshu_feed_size(self):
        output = render_social_page(self.page, self.root / "page-01.png")

        self.assertEqual(self.root / "page-01.png", output)
        with Image.open(output) as rendered:
            self.assertEqual((1080, 1440), rendered.size)

    def test_social_renderer_rejects_non_3x4_source(self):
        Image.new("RGB", (1200, 1200), "white").save(self.source)

        with self.assertRaisesRegex(ValueError, "源图必须是3:4"):
            render_social_page(self.page, self.root / "page-01.png")

    def test_social_renderer_explicit_9x16_preserves_legacy_output(self):
        self.page["layout_design"] = valid_layout_design("social-vertical-9x16")
        Image.new("RGB", (900, 1600), (120, 160, 200)).save(self.source)

        output = render_social_page(
            self.page,
            self.root / "legacy-page-01.png",
            profile="social-vertical-9x16",
        )

        with Image.open(output) as rendered:
            self.assertEqual((1080, 1920), rendered.size)

    def test_social_renderer_rejects_text_outside_safe_area(self):
        self.page["layout_design"]["social_layout"]["text_safe_area"] = [0.08, 0.82, 0.84, 0.015]
        self.page["text"] = "这是一段无法放入过小字幕安全区的文字。"

        with self.assertRaisesRegex(ValueError, "字幕超出文字安全区"):
            render_social_page(self.page, self.root / "page-01.png")


if __name__ == "__main__":
    unittest.main()
