from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.validate_project import aggregate_reports, validate_project


ROOT = Path(__file__).resolve().parents[1]


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

    def test_golden_phase2_cli_passes_without_writing(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "golden-phase2"
        report_path = fixture / "validation-report.json"
        before = report_path.read_text(encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate_project.py"),
                str(fixture),
                "--stage",
                "phase2",
                "--no-write",
            ],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["final_status"], "概念提案可用")
        self.assertEqual(report["quality_score"], 100)
        self.assertEqual(report_path.read_text(encoding="utf-8"), before)

    def test_golden_phase2_direct_orchestration_passes(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "golden-phase2"
        report = validate_project(fixture, "phase2")
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["adapters"], ["technology-manufacturing"])

    def test_missing_project_collects_structured_and_delivery_errors(self) -> None:
        report = validate_project(ROOT / "tests" / "fixtures" / "does-not-exist", "phase1")
        self.assertEqual(report["status"], "FAIL")
        codes = {item["code"] for item in report["issues"]}
        self.assertIn("JSON_FILE_NOT_FOUND", codes)
        self.assertIn("PACKAGE_NOT_FOUND", codes)


if __name__ == "__main__":
    unittest.main()
