from __future__ import annotations

import copy
import unittest

from scripts.validate_input_manifest import normalize_manifest, validate_manifest


def v1_manifest() -> dict:
    return {
        "project": {
            "name": "测试展厅",
            "company_name": "测试企业",
            "objective": "建立客户信任",
            "audiences": ["客户", "合作伙伴"],
        },
        "brand_materials": [{"name": "企业介绍", "path": "企业介绍.pdf"}],
        "space": {},
        "evidence": [],
    }


class InputManifestV2Tests(unittest.TestCase):
    def test_v1_is_normalized_in_memory_without_mutating_source(self) -> None:
        source = v1_manifest()
        original = copy.deepcopy(source)
        normalized, warnings = normalize_manifest(source)
        self.assertEqual(source, original)
        self.assertEqual(normalized["schema_version"], "2.0")
        self.assertEqual([item["id"] for item in normalized["audiences"]], ["A01", "A02"])
        self.assertTrue(any(item["code"] == "V1_MANIFEST_NORMALIZED" for item in warnings))

    def test_v1_remains_compatible_but_reports_degraded_fields(self) -> None:
        report = validate_manifest(v1_manifest(), "phase1")
        self.assertNotEqual(report["status"], "FAIL")
        codes = {item["code"] for item in report["issues"]}
        self.assertIn("V1_MANIFEST_NORMALIZED", codes)
        self.assertIn("FLOOR_PLAN_MISSING", codes)

    def test_phase2_requires_complete_confirmation_record(self) -> None:
        data, _ = normalize_manifest(v1_manifest())
        data["storyline"] = {"confirmed": True, "selected_id": "S01"}
        report = validate_manifest(data, "phase2")
        self.assertIn("STORYLINE_CONFIRMATION_INCOMPLETE", {item["code"] for item in report["issues"]})

    def test_enterprise_and_design_evidence_use_separate_id_lanes(self) -> None:
        data, _ = normalize_manifest(v1_manifest())
        data["evidence"] = [
            {
                "id": "D001",
                "claim": "企业成立于 2000 年",
                "source": "企业官网",
                "source_type": "company_official",
                "status": "已核实",
                "locator": "关于我们",
            }
        ]
        report = validate_manifest(data, "phase1")
        self.assertIn("EVIDENCE_ID_INVALID", {item["code"] for item in report["issues"]})


if __name__ == "__main__":
    unittest.main()
