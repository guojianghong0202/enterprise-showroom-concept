from __future__ import annotations

import unittest

from scripts.validation_common import make_issue, summarize_issues, valid_id


class ValidationCommonTests(unittest.TestCase):
    def test_issue_schema_and_summary_are_stable(self) -> None:
        issues = [
            make_issue("BLOCKER", "BROKEN", "阻断", file="a.json", json_path="zones[0]", related_ids=["Z01"]),
            make_issue("WARNING", "CHECK", "复核"),
        ]
        self.assertEqual(issues[0]["related_ids"], ["Z01"])
        self.assertEqual(summarize_issues(issues), {"blockers": 1, "warnings": 1})

    def test_stable_identifier_rules(self) -> None:
        self.assertTrue(valid_id("E001", "E"))
        self.assertTrue(valid_id("A01", "A"))
        self.assertFalse(valid_id("E01", "E"))
        self.assertFalse(valid_id("Z001", "Z"))


if __name__ == "__main__":
    unittest.main()
