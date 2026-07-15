from __future__ import annotations

import unittest

from scripts.validate_project import aggregate_reports


class ValidateProjectTests(unittest.TestCase):
    def test_aggregate_preserves_diagnostic_fields_and_status(self) -> None:
        reports = [
            {"issues": [{"level": "WARNING", "code": "A", "message": "复核", "json_path": "space"}]},
            {"issues": [{"level": "BLOCKER", "code": "B", "message": "阻断", "related_ids": ["Z01"]}]},
        ]
        report = aggregate_reports(reports, stage="phase2", adapters=["generic"])
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["summary"], {"blockers": 1, "warnings": 1})
        self.assertEqual(report["issues"][1]["related_ids"], ["Z01"])
        self.assertEqual(report["adapters"], ["generic"])


if __name__ == "__main__":
    unittest.main()
