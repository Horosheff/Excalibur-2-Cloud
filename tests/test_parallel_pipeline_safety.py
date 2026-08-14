"""Tests for idempotent handoff fragment merge."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _write_fragment(path: Path, role: str, marker: str, topic_id: str) -> None:
    path.write_text(
        f"---\nrole: excalibur-blog-{role}\ntopic_id: {topic_id}\nstatus: PASS\n"
        "completed_at: 2026-07-20T00:00:00Z\nincident_report: none\n---\n"
        f"=== EXCALIBUR BLOG {marker} ===\ntopic_id: {topic_id}\n",
        encoding="utf-8",
    )


class ParallelPipelineSafetyTest(unittest.TestCase):
    def test_handoff_merge_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "handoff.md"
            handoff.write_text("# handoff\ntopic_id: B65\n", encoding="utf-8")
            fragments = root / "fragments"
            fragments.mkdir()
            for role, marker in (("cover", "COVER"), ("schema", "SCHEMA")):
                _write_fragment(fragments / f"{role}.md", role, marker, "B65")
            cmd = [
                sys.executable, str(ROOT / "scripts/excalibur_blog_handoff_merge.py"),
                "--handoff", str(handoff), "--fragments-dir", str(fragments),
                "--wave", "cover,schema",
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            text = handoff.read_text(encoding="utf-8")
            self.assertEqual(text.count("=== EXCALIBUR BLOG COVER ==="), 1)
            self.assertEqual(text.count("=== EXCALIBUR BLOG SCHEMA ==="), 1)

    def test_stale_fragment_topic_id_rejected(self) -> None:
        """INC-20260810-1620: merge must not stitch prior-run fragment."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "handoff.md"
            handoff.write_text(
                "=== EXCALIBUR BLOG SCOUT ===\ntopic_id: B156\n",
                encoding="utf-8",
            )
            fragments = root / "fragments"
            fragments.mkdir()
            _write_fragment(fragments / "schema.md", "schema", "SCHEMA", "B155")
            cmd = [
                sys.executable, str(ROOT / "scripts/excalibur_blog_handoff_merge.py"),
                "--handoff", str(handoff), "--fragments-dir", str(fragments),
                "--wave", "schema",
                "--expect-topic-id", "B156",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("B155", proc.stderr)
            self.assertIn("B156", proc.stderr)
            self.assertNotIn(
                "=== EXCALIBUR BLOG SCHEMA ===",
                handoff.read_text(encoding="utf-8"),
            )

    def test_expect_topic_id_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "handoff.md"
            handoff.write_text(
                "=== EXCALIBUR BLOG SCOUT ===\ntopic_id: B156\n",
                encoding="utf-8",
            )
            fragments = root / "fragments"
            fragments.mkdir()
            _write_fragment(fragments / "schema.md", "schema", "SCHEMA", "B156")
            cmd = [
                sys.executable, str(ROOT / "scripts/excalibur_blog_handoff_merge.py"),
                "--handoff", str(handoff), "--fragments-dir", str(fragments),
                "--wave", "schema",
                "--expect-topic-id", "B156",
            ]
            proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
            self.assertIn("topic_id=B156", proc.stdout)
            text = handoff.read_text(encoding="utf-8")
            self.assertIn("=== EXCALIBUR BLOG SCHEMA ===", text)
            self.assertIn("topic_id: B156", text)


if __name__ == "__main__":
    unittest.main()
