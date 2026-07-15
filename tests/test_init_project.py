from __future__ import annotations

import unittest

from scripts.init_project import build_initial_manifest, phase_file_names


class InitProjectTests(unittest.TestCase):
    def test_initial_manifest_uses_v2_schema_and_stable_audience_id(self) -> None:
        data = build_initial_manifest("示例项目", "示例企业")
        self.assertEqual(data["schema_version"], "2.0")
        self.assertEqual(data["project"]["name"], "示例项目")
        self.assertEqual(data["audiences"][0]["id"], "A01")

    def test_phase1_and_phase2_file_sets_respect_stage_gate(self) -> None:
        self.assertEqual(len(phase_file_names("phase1")), 2)
        self.assertEqual(len(phase_file_names("phase2")), 6)


if __name__ == "__main__":
    unittest.main()
