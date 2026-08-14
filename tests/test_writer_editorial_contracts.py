"""Guard human-first Writer meaning + Sol style boundaries."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WriterEditorialContractsTest(unittest.TestCase):
    def test_writer_master_is_meaning_only(self) -> None:
        prompt = (ROOT / "shared/writer-master-prompt.md").read_text(encoding="utf-8")
        self.assertIn("drafts/writer.html", prompt)
        self.assertIn("research-notes.md", prompt)
        self.assertIn("title-brief.json", prompt)
        self.assertIn("published-titles-only.md", prompt)
        self.assertIn("Sol", prompt)
        self.assertNotIn("lead.md", prompt)

        canon = json.loads((ROOT / "shared/pipeline-canon.json").read_text(encoding="utf-8"))
        self.assertEqual(
            canon["writer_allowed_sources"],
            [
                "shared/writer-master-prompt.md",
                "research-notes.md",
                "title-brief.json",
                "published-titles-only.md",
                "shared/dzen-content-rules.md",
                "shared/rf-blocked-entities.json",
            ],
        )

    def test_writer_skill_meaning_draft(self) -> None:
        skill = (ROOT / "skills/writer-excalibur-blog/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("drafts/writer.html", skill)
        self.assertIn("published-titles-only.md", skill)
        self.assertIn("Sol", skill)

    def test_soul_layer_present(self) -> None:
        soul = (ROOT / "shared/SOUL.md").read_text(encoding="utf-8")
        good = (ROOT / "shared/soul-examples/good-outputs.md").read_text(encoding="utf-8")
        bad = (ROOT / "shared/soul-examples/bad-outputs.md").read_text(encoding="utf-8")
        post = (ROOT / "shared/soul-examples/post-to-article.md").read_text(encoding="utf-8")
        src = (ROOT / "shared/soul-examples/SOURCE.md").read_text(encoding="utf-8")
        self.assertIn("Core Truths", soul)
        self.assertIn("excalibur-blog-sol", soul)
        self.assertIn("Vibe", soul)
        self.assertIn("SETUP_REQUIRED", good)
        self.assertIn("Calibration", good)
        self.assertIn("SETUP_REQUIRED", src)
        self.assertIn("битов", post.lower())
        self.assertIn("seo-робот", bad.lower())
        self.assertIn("чужой голос", bad.lower())

    def test_pipeline_canon_lists_sol_sources(self) -> None:
        canon = json.loads((ROOT / "shared/pipeline-canon.json").read_text(encoding="utf-8"))
        self.assertIn("shared/SOUL.md", canon["sol_allowed_sources"])
        self.assertIn("drafts/writer.html", canon["sol_allowed_sources"])
        self.assertTrue(canon["sol_is_final"])
        self.assertFalse(canon["writer_is_final"])
        self.assertIn("memory/blog/articles/*/article.html", canon["writer_forbidden_sources"])
        self.assertEqual(canon["opening_rules"].get("soul"), "shared/SOUL.md")

    def test_published_titles_script_never_reads_html(self) -> None:
        source = (ROOT / "scripts/excalibur_blog_published_titles.py").read_text(encoding="utf-8")
        self.assertIn("article.meta.json", source)
        self.assertIn("never article.html", source.lower())
        self.assertNotIn('/ "article.html"', source)
        self.assertNotIn('article_dir / "article.html"', source)

    def test_published_titles_builds_from_meta_only(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "scripts"))
        from excalibur_blog_published_titles import write_titles

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared = root / "shared"
            shared.mkdir(parents=True)
            (shared / "published-articles.md").write_text(
                "# ledger\n\n"
                "| date | topic_id | slug | url | status |\n"
                "|------|----------|------|-----|--------|\n"
                "| 2026-08-10 | B01 | demo-slug | /demo-slug/ | published |\n",
                encoding="utf-8",
            )
            article_dir = root / "memory" / "blog" / "articles" / "B01-demo-slug"
            article_dir.mkdir(parents=True)
            (article_dir / "article.meta.json").write_text(
                '{"topic_id":"B01","slug":"demo-slug","title":"Демо заголовок"}\n',
                encoding="utf-8",
            )
            (article_dir / "article.html").write_text(
                "<p>BODY MUST NOT APPEAR IN TITLES FILE</p>\n",
                encoding="utf-8",
            )
            out_dir = root / "out"
            result = write_titles(root, article_dir=out_dir)
            text = (out_dir / "published-titles-only.md").read_text(encoding="utf-8")
            self.assertEqual(result["count"], 1)
            self.assertIn("Демо заголовок", text)
            self.assertNotIn("BODY MUST NOT APPEAR", text)

    def test_writer_ready_gate_has_no_critic_contract(self) -> None:
        gate = (ROOT / "scripts/excalibur_blog_writer_ready_gate.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("critic-report", gate)
        self.assertIn("forbidden choice key", gate)
        self.assertFalse((ROOT / "agents/excalibur-blog-article-editor.md").exists())


if __name__ == "__main__":
    unittest.main()
