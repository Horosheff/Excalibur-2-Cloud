"""Titles-only memory: 30-day window + purge helpers."""
from __future__ import annotations

import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "scripts"))

from excalibur_blog_published_titles import (  # noqa: E402
    build_titles,
    load_ledger_rows,
    parse_iso_date,
)
from excalibur_blog_memory_purge import (  # noqa: E402
    topic_from_dirname,
)


class TitlesOnlyMemoryTest(unittest.TestCase):
    def test_parse_iso_date(self) -> None:
        self.assertEqual(parse_iso_date("2026-08-11"), date(2026, 8, 11))
        self.assertIsNone(parse_iso_date("nope"))

    def test_build_titles_respects_30_day_window(self) -> None:
        import tempfile

        as_of = date(2026, 8, 14)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared = root / "shared"
            shared.mkdir()
            (shared / "published-articles.md").write_text(
                "# ledger\n\n"
                "| date | topic_id | slug | url | status |\n"
                "|------|----------|------|-----|--------|\n"
                "| 2026-06-01 | B01 | old-slug | /old/ | published |\n"
                "| 2026-08-10 | B02 | new-slug | /new/ | published |\n"
                "| 2026-08-12 | B03 | draft-slug | /d/ | in_progress |\n",
                encoding="utf-8",
            )
            (root / "memory/blog/articles").mkdir(parents=True)
            rows = build_titles(
                root,
                statuses={"published"},
                days=30,
                as_of=as_of,
                previous_titles={"B02": "Свежий заголовок"},
            )
            cutoff = as_of - timedelta(days=30)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["topic_id"], "B02")
            self.assertEqual(rows[0]["title"], "Свежий заголовок")
            for row in rows:
                d = parse_iso_date(row["date"])
                self.assertIsNotNone(d)
                assert d is not None
                self.assertGreaterEqual(d, cutoff, row)
                self.assertEqual(row["status"], "published")

    def test_shared_titles_file_mentions_30_day_window(self) -> None:
        text = (ROOT / "shared/published-titles.md").read_text(encoding="utf-8")
        self.assertIn("30", text)
        self.assertIn("anti-dup", text.lower())
        self.assertNotIn("draft_ready", text)

    def test_topic_from_dirname(self) -> None:
        self.assertEqual(
            topic_from_dirname("B159-openai-vypustila-kibermodel-tolko-dlya-zaschitnikov"),
            "B159",
        )

    def test_ledger_loader_reads_status(self) -> None:
        rows = load_ledger_rows(ROOT)
        self.assertIsInstance(rows, list)


if __name__ == "__main__":
    unittest.main()
