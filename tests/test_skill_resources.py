from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillResourceTests(unittest.TestCase):
    def test_skill_is_compact_and_links_every_reference_directly(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(skill.splitlines()), 200)
        linked = set(re.findall(r"references/([A-Za-z0-9._-]+\.md)", skill))
        actual = {path.name for path in (ROOT / "references").glob("*.md")}
        self.assertEqual(linked, actual)

    def test_v2_control_and_delivery_templates_exist(self) -> None:
        expected = {
            "project-manifest-template.json",
            "design-model-template.json",
            "validation-report-template.json",
            "diagnosis-template.md",
            "story-comparison-template.md",
            "concept-document-template.md",
            "ppt-page-script-template.md",
            "render-prompt-template.md",
            "sources-and-open-questions-template.md",
        }
        actual = {path.name for path in (ROOT / "assets").iterdir() if path.is_file()}
        self.assertTrue(expected <= actual, expected - actual)

    def test_skill_documents_two_stage_gate_and_structured_ids(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for token in ("confirmed_at", "confirmation_note", "project-manifest.json", "design-model.json", "A/E/D/S/Z/R/X/P"):
            self.assertIn(token, skill)


if __name__ == "__main__":
    unittest.main()
