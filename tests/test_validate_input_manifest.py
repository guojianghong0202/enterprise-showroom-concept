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


def complete_v2_manifest() -> dict:
    data, _ = normalize_manifest(v1_manifest())
    data["space"] = {
        "area_sqm": 300,
        "ceiling_height_m": 4,
        "floor_plan": "plan.pdf",
        "entrances": ["入口"],
        "exits": ["出口"],
        "confidence": "high",
    }
    data["evidence"] = [
        {
            "id": "E001",
            "claim": "企业事实",
            "source": "企业官网",
            "source_type": "company_official",
            "status": "已核实",
            "locator": "关于我们",
        }
    ]
    return data


class InputManifestV2Tests(unittest.TestCase):
    def test_complete_v2_phase1_passes(self) -> None:
        report = validate_manifest(complete_v2_manifest(), "phase1")
        self.assertEqual(report["status"], "PASS", report)

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

    def test_invalid_project_audience_space_and_adapter_fields_are_reported(self) -> None:
        data = complete_v2_manifest()
        data["project"]["objective"] = ""
        data["project"]["budget_tier"] = "premium"
        data["project"]["adapters"] = ["a", "b", "c"]
        data["audiences"] = ["客户", {"id": "A1", "name": ""}, {"id": "A01", "name": "客户"}, {"id": "A01", "name": "伙伴"}]
        data["space"]["confidence"] = "certain"
        report = validate_manifest(data, "phase1")
        codes = {item["code"] for item in report["issues"]}
        self.assertTrue(
            {
                "PROJECT_FIELD_MISSING",
                "BUDGET_TIER_INVALID",
                "ADAPTER_COUNT_INVALID",
                "AUDIENCE_INVALID",
                "AUDIENCE_ID_INVALID",
                "AUDIENCE_NAME_MISSING",
                "AUDIENCE_ID_DUPLICATE",
                "SPACE_CONFIDENCE_INVALID",
            }
            <= codes
        )

    def test_missing_materials_space_and_phase2_evidence_are_reported(self) -> None:
        data = complete_v2_manifest()
        data["brand_materials"] = []
        data["space"] = {"confidence": "unknown"}
        data["evidence"] = []
        report = validate_manifest(data, "phase2")
        codes = {item["code"] for item in report["issues"]}
        self.assertTrue(
            {
                "BRAND_MATERIALS_MISSING",
                "SPACE_DIMENSIONS_MISSING",
                "FLOOR_PLAN_MISSING",
                "ACCESS_POINTS_MISSING",
                "EVIDENCE_MISSING",
                "STORYLINE_NOT_CONFIRMED",
            }
            <= codes
        )

    def test_evidence_conflicts_duplicates_and_incomplete_content_are_reported(self) -> None:
        data = complete_v2_manifest()
        data["evidence"] = [
            {
                "id": "E001",
                "claim": "",
                "source": "",
                "source_type": "third_party_news",
                "status": "来源冲突",
                "locator": "",
            },
            {
                "id": "E001",
                "claim": "重复",
                "source": "年报",
                "source_type": "annual_report",
                "status": "未知",
                "locator": "第1页",
            },
            {
                "id": "",
                "claim": "无编号",
                "source": "官网",
                "source_type": "company_official",
                "status": "已核实",
                "locator": "正文",
            },
        ]
        report = validate_manifest(data, "phase1")
        codes = {item["code"] for item in report["issues"]}
        self.assertTrue(
            {
                "EVIDENCE_ID_DUPLICATE",
                "EVIDENCE_ID_MISSING",
                "SOURCE_TYPE_NOT_ALLOWED",
                "EVIDENCE_STATUS_INVALID",
                "EVIDENCE_CONTENT_MISSING",
                "EVIDENCE_LOCATOR_MISSING",
                "CONFLICT_RECORD_MISSING",
            }
            <= codes
        )

    def test_design_reference_validation_covers_source_content_and_duplicates(self) -> None:
        data = complete_v2_manifest()
        data["design_references"] = [
            {"id": "D01", "source_type": "blog"},
            {
                "id": "D001",
                "source_type": "design_award",
                "source": "奖项官网",
                "purpose": "案例",
                "takeaway": "方法",
                "limitations": "边界",
            },
            {
                "id": "D001",
                "source_type": "design_award",
                "source": "另一个页面",
                "purpose": "案例",
                "takeaway": "方法",
                "limitations": "边界",
            },
        ]
        report = validate_manifest(data, "phase1")
        codes = {item["code"] for item in report["issues"]}
        self.assertTrue(
            {
                "DESIGN_REFERENCE_ID_INVALID",
                "DESIGN_SOURCE_TYPE_NOT_ALLOWED",
                "DESIGN_REFERENCE_CONTENT_MISSING",
                "DESIGN_REFERENCE_ID_DUPLICATE",
            }
            <= codes
        )

    def test_complete_phase2_confirmation_passes(self) -> None:
        data = complete_v2_manifest()
        data["storyline"] = {
            "confirmed": True,
            "selected_id": "S01",
            "confirmed_at": "2026-07-15T15:00:00+08:00",
            "confirmation_note": "用户确认 S01",
        }
        report = validate_manifest(data, "phase2")
        self.assertEqual(report["status"], "PASS", report)

    def test_malformed_evidence_item_is_reported_instead_of_crashing(self) -> None:
        data = complete_v2_manifest()
        data["evidence"] = ["not-an-object"]
        report = validate_manifest(data, "phase1")
        self.assertIn("EVIDENCE_INVALID", {item["code"] for item in report["issues"]})


if __name__ == "__main__":
    unittest.main()
