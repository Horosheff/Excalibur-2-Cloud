"""Tenant cover watermark is optional and skips when not configured."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CoverWatermarkTenantTest(unittest.TestCase):
    def test_skip_when_not_configured(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "scripts"))
        from excalibur_blog_cover_brand_watermark import load_cfg

        cfg = load_cfg(ROOT)
        self.assertIsNone(cfg)

    def test_quad_apply_wires_optional_watermark(self) -> None:
        src = (ROOT / "scripts/excalibur_blog_quad_apply.py").read_text(encoding="utf-8")
        self.assertIn("excalibur_blog_cover_brand_watermark.py", src)
        self.assertIn("skip-brand-watermark", src)


if __name__ == "__main__":
    unittest.main()
