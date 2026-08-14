"""Guard Cloud Automation canon + cost rules stay aligned with pipeline-canon."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CloudAutomationCanonTest(unittest.TestCase):
    def test_cloud_cost_rules_exist_and_bound_tasks(self) -> None:
        p = ROOT / "shared/cloud-cost-rules.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        low = text.lower()
        self.assertTrue("запрещено" in low or "запрещён" in low or "запрещен" in low)
        self.assertIn("Task(", text)
        self.assertIn("один", low)
        self.assertIn("status: open", text)
        self.assertIn("llms-full.txt", text)

    def test_cloud_automation_matches_human_first_v2(self) -> None:
        canon = json.loads((ROOT / "shared/pipeline-canon.json").read_text(encoding="utf-8"))
        text = (ROOT / "CLOUD-AUTOMATION.md").read_text(encoding="utf-8")
        self.assertEqual(canon.get("version"), "human-first-v2")
        self.assertIn("Sol", text)
        self.assertIn("Description", text)
        self.assertIn("cloud-cost-rules", text)
        self.assertIn("0 10 * * *", text)
        self.assertNotIn("Writer пишет ФИНАЛЬНЫЙ", text)
        self.assertNotIn("Editor → GEO QA", text)
        self.assertIn("## Automation prompt", text)
        self.assertIn("Ты Директор Excalibur BLOG", text)
        self.assertIn("ЗАПРЕЩЕНО вызывать Task", text)

    def test_cursorignore_keeps_heavy_assets_out(self) -> None:
        ign = (ROOT / ".cursorignore").read_text(encoding="utf-8")
        self.assertIn("llms-full.txt", ign)
        self.assertIn("cover/*.png", ign)

    def test_director_skill_fixer_shell_first(self) -> None:
        skill = (ROOT / "skills/director-excalibur-blog/SKILL.md").read_text(encoding="utf-8")
        low = skill.lower()
        self.assertIn("cloud-cost-rules", skill)
        self.assertIn("status: open", skill)
        self.assertIn("запрещено", low)
        self.assertIn("task(", low)
        self.assertIn("этой же сессии", low)


if __name__ == "__main__":
    unittest.main()
