from __future__ import annotations

import unittest

from scripts.validation_common import build_report, load_json, make_issue, status_from_summary, summarize_issues, valid_id, write_json


class FakeJsonPath:
    def __init__(self, content: str | Exception):
        self.name = "data.json"
        self.content = content
        self.written: tuple[str, str] | None = None

    def read_text(self, encoding: str) -> str:
        if isinstance(self.content, Exception):
            raise self.content
        return self.content

    def write_text(self, content: str, encoding: str) -> None:
        self.written = (content, encoding)


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

    def test_report_statuses_and_extra_fields(self) -> None:
        self.assertEqual(status_from_summary({"blockers": 0, "warnings": 0}), "PASS")
        self.assertEqual(status_from_summary({"blockers": 0, "warnings": 1}), "PASS_WITH_WARNINGS")
        self.assertEqual(status_from_summary({"blockers": 1, "warnings": 0}), "FAIL")
        report = build_report([], stage="phase1", validator="test", root="memory")
        self.assertEqual(report["root"], "memory")

    def test_json_loading_and_writing_helpers(self) -> None:
        path = FakeJsonPath('{"name": "展厅"}')
        data, error = load_json(path)  # type: ignore[arg-type]
        self.assertEqual(data, {"name": "展厅"})
        self.assertIsNone(error)

        data, error = load_json(FakeJsonPath("[]"))  # type: ignore[arg-type]
        self.assertIsNone(data)
        self.assertEqual(error["code"], "JSON_ROOT_INVALID")

        data, error = load_json(FakeJsonPath("{invalid"))  # type: ignore[arg-type]
        self.assertIsNone(data)
        self.assertEqual(error["code"], "JSON_FILE_INVALID")

        data, error = load_json(FakeJsonPath(FileNotFoundError("missing")))  # type: ignore[arg-type]
        self.assertIsNone(data)
        self.assertEqual(error["code"], "JSON_FILE_NOT_FOUND")

        output = FakeJsonPath("")
        write_json(output, {"name": "展厅"})  # type: ignore[arg-type]
        self.assertEqual(output.written[1], "utf-8")
        self.assertIn('"展厅"', output.written[0])


if __name__ == "__main__":
    unittest.main()
