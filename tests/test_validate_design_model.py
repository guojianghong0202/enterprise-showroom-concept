from __future__ import annotations

import copy
import unittest

from scripts.validate_design_model import validate_design_model


def phase1_model() -> dict:
    return {
        "schema_version": "2.0",
        "project_id": "test-showroom",
        "derived_from_manifest": "project-manifest.json",
        "phase": "phase1",
        "strategy": {"audience_ids": ["A01"], "core_claim": "用可验证能力建立信任"},
        "story_candidates": [
            {
                "id": "S01",
                "title": "能力如何形成",
                "audience_ids": ["A01"],
                "proposition": "展示能力形成过程",
                "spatial_archetype": "递进式能力链",
                "signature_exhibit": "透明工艺模型",
                "emotional_arc": "理解—验证—信任",
                "visual_motif": "精密层叠",
            },
            {
                "id": "S02",
                "title": "价值如何发生",
                "audience_ids": ["A01"],
                "proposition": "从客户问题进入案例",
                "spatial_archetype": "场景岛链",
                "signature_exhibit": "案例推演台",
                "emotional_arc": "共鸣—发现—行动",
                "visual_motif": "连接网络",
            },
        ],
        "selected_story": None,
        "space_program": {},
        "routes": [],
        "zones": [],
        "exhibits": [],
        "visual_system": {},
        "wayfinding_system": {},
        "budget_strategies": [],
        "accessibility_review": {},
        "ppt_pages": [],
        "assumptions": [],
        "risks": [],
        "open_questions": [],
    }


def manifest(space_confidence: str = "high") -> dict:
    return {
        "schema_version": "2.0",
        "project": {"expected_visit_minutes": {"min": 20, "max": 30}},
        "space": {"confidence": space_confidence, "entrances": ["入口"], "exits": ["出口"]},
    }


def phase2_model() -> dict:
    data = phase1_model()
    data.update(
        {
            "phase": "phase2",
            "selected_story": "S01",
            "space_program": {"allocation_mode": "range", "placement_status": "conceptual"},
            "routes": [
                {
                    "id": "R01",
                    "name": "主路线",
                    "zone_ids": ["Z01", "Z02"],
                    "start": "入口",
                    "end": "出口",
                    "duration_minutes": {"min": 20, "max": 30},
                }
            ],
            "zones": [
                {
                    "id": "Z01",
                    "name": "序厅",
                    "priority": "key",
                    "area_range_pct": {"min": 35, "max": 45},
                    "adjacent_to": ["Z02"],
                    "exhibit_ids": ["X01"],
                    "visual_direction": "品牌证据入口",
                    "wayfinding": "章节门槛",
                    "render_handoff": "入口广角",
                    "open_questions": ["入口净宽待专业复核"],
                },
                {
                    "id": "Z02",
                    "name": "能力厅",
                    "priority": "key",
                    "area_range_pct": {"min": 55, "max": 65},
                    "adjacent_to": ["Z01"],
                    "exhibit_ids": ["X02"],
                    "visual_direction": "工艺层叠",
                    "wayfinding": "方向确认",
                    "render_handoff": "核心展项视角",
                    "open_questions": ["展项尺寸待图纸复核"],
                },
            ],
            "exhibits": [
                {
                    "id": "X01",
                    "zone_id": "Z01",
                    "objective": "建立第一认知",
                    "content": "总主张",
                    "media_type": "graphic",
                    "low_tech_fallback": "静态主张墙",
                    "operations": "季度更新",
                    "inclusion_notes": "保持文字对比度并复核观看距离",
                    "budget_tiers": ["basic", "standard", "flagship"],
                },
                {
                    "id": "X02",
                    "zone_id": "Z02",
                    "objective": "理解核心能力",
                    "content": "工艺与质量证据",
                    "media_type": "model",
                    "low_tech_fallback": "剖切模型与图文",
                    "operations": "每年内容复核",
                    "inclusion_notes": "提供不依赖触控的替代说明",
                    "budget_tiers": ["standard", "flagship"],
                },
            ],
            "visual_system": {"brand_translation": "品牌结构转译", "anti_generic_check": "与工艺层叠绑定"},
            "wayfinding_system": {"levels": ["入口", "章节", "方向", "出口"]},
            "budget_strategies": [
                {"tier": "basic", "cost_drivers": ["图文"], "maintenance": "低"},
                {"tier": "standard", "cost_drivers": ["模型"], "maintenance": "中"},
                {"tier": "flagship", "cost_drivers": ["沉浸媒体"], "maintenance": "高"},
            ],
            "accessibility_review": {"route": "概念级连续性检查", "professional_review": ["通行与设备安装"]},
            "ppt_pages": [
                {"id": "P01", "decision_question": "为什么可信", "story_id": "S01", "zone_ids": ["Z01"], "exhibit_ids": ["X01"], "source_section": "项目定位"},
                {"id": "P02", "decision_question": "能力如何证明", "story_id": "S01", "zone_ids": ["Z02"], "exhibit_ids": ["X02"], "source_section": "展区内容卡"},
            ],
        }
    )
    return data


class DesignModelV2Tests(unittest.TestCase):
    def test_phase1_accepts_two_substantively_different_candidates(self) -> None:
        report = validate_design_model(phase1_model(), manifest(), "phase1")
        self.assertEqual(report["summary"]["blockers"], 0, report)

    def test_phase2_complete_model_passes_structural_checks(self) -> None:
        report = validate_design_model(phase2_model(), manifest(), "phase2")
        self.assertEqual(report["summary"]["blockers"], 0, report)

    def test_hanging_reference_and_disconnected_zone_are_blocked(self) -> None:
        data = phase2_model()
        data["routes"][0]["zone_ids"].append("Z99")
        data["zones"][0]["adjacent_to"] = []
        data["zones"][1]["adjacent_to"] = []
        report = validate_design_model(data, manifest(), "phase2")
        codes = {item["code"] for item in report["issues"]}
        self.assertIn("REFERENCE_NOT_FOUND", codes)
        self.assertIn("ZONE_GRAPH_DISCONNECTED", codes)

    def test_impossible_area_range_is_blocked(self) -> None:
        data = phase2_model()
        data["zones"][0]["area_range_pct"] = {"min": 60, "max": 70}
        data["zones"][1]["area_range_pct"] = {"min": 55, "max": 65}
        report = validate_design_model(data, manifest(), "phase2")
        self.assertIn("AREA_RANGE_INVALID", {item["code"] for item in report["issues"]})

    def test_low_confidence_cannot_claim_confirmed_placement(self) -> None:
        data = phase2_model()
        data["space_program"]["placement_status"] = "confirmed"
        report = validate_design_model(data, manifest("low"), "phase2")
        self.assertIn("LOW_CONFIDENCE_OVERCLAIM", {item["code"] for item in report["issues"]})

    def test_exhibit_requires_fallback_operations_and_inclusion(self) -> None:
        data = copy.deepcopy(phase2_model())
        data["exhibits"][0]["low_tech_fallback"] = ""
        data["exhibits"][0]["operations"] = ""
        data["exhibits"][0]["inclusion_notes"] = ""
        report = validate_design_model(data, manifest(), "phase2")
        self.assertIn("EXHIBIT_FIELD_MISSING", {item["code"] for item in report["issues"]})

    def test_story_count_incomplete_and_similarity_are_blocked(self) -> None:
        data = phase1_model()
        data["story_candidates"] = [copy.deepcopy(data["story_candidates"][0])]
        report = validate_design_model(data, manifest(), "phase1")
        self.assertIn("STORY_CANDIDATE_COUNT_INVALID", {item["code"] for item in report["issues"]})

        data = phase1_model()
        data["story_candidates"][1] = copy.deepcopy(data["story_candidates"][0])
        data["story_candidates"][1]["id"] = "S02"
        data["story_candidates"][1]["visual_motif"] = "另一种色彩"
        data["story_candidates"][0]["signature_exhibit"] = ""
        report = validate_design_model(data, manifest(), "phase1")
        codes = {item["code"] for item in report["issues"]}
        self.assertIn("STORY_CANDIDATE_INCOMPLETE", codes)
        self.assertIn("STORY_CANDIDATES_TOO_SIMILAR", codes)

    def test_schema_phase_and_identifier_errors_are_blocked(self) -> None:
        data = phase2_model()
        data["schema_version"] = "1.0"
        data["phase"] = "phase1"
        data["story_candidates"][0]["id"] = "S1"
        data["zones"][1]["id"] = "Z01"
        data["routes"][0]["id"] = "route"
        data["exhibits"][0]["id"] = "X1"
        data["ppt_pages"][0]["id"] = "P1"
        report = validate_design_model(data, manifest(), "phase2")
        codes = {item["code"] for item in report["issues"]}
        self.assertTrue({"DESIGN_SCHEMA_INVALID", "DESIGN_PHASE_MISMATCH", "ID_FORMAT_INVALID", "ID_DUPLICATE"} <= codes)

    def test_selected_story_exhibit_and_ppt_references_must_exist(self) -> None:
        data = phase2_model()
        data["selected_story"] = "S99"
        data["exhibits"][0]["zone_id"] = "Z99"
        data["zones"][0]["exhibit_ids"] = ["X99"]
        data["ppt_pages"][0]["story_id"] = "S99"
        data["ppt_pages"][0]["exhibit_ids"] = ["X99"]
        report = validate_design_model(data, manifest(), "phase2")
        self.assertGreaterEqual([item["code"] for item in report["issues"]].count("REFERENCE_NOT_FOUND"), 5)

    def test_exact_area_and_missing_area_modes_are_checked(self) -> None:
        data = phase2_model()
        data["space_program"]["allocation_mode"] = "exact"
        data["zones"][0]["area_pct"] = 40
        data["zones"][1]["area_pct"] = 40
        report = validate_design_model(data, manifest(), "phase2")
        self.assertIn("AREA_TOTAL_INVALID", {item["code"] for item in report["issues"]})

        data = phase2_model()
        data["space_program"]["allocation_mode"] = "range"
        data["zones"][0].pop("area_range_pct")
        report = validate_design_model(data, manifest(), "phase2")
        self.assertIn("AREA_RANGE_MISSING", {item["code"] for item in report["issues"]})

        data = phase2_model()
        data["space_program"]["allocation_mode"] = "unknown"
        report = validate_design_model(data, manifest(), "phase2")
        self.assertIn("AREA_MODE_INVALID", {item["code"] for item in report["issues"]})

    def test_route_endpoint_duration_zone_and_system_gaps_are_reported(self) -> None:
        data = phase2_model()
        data["routes"][0]["start"] = "错误入口"
        data["routes"][0]["duration_minutes"] = {"min": 40, "max": 50}
        data["zones"][0]["visual_direction"] = ""
        data["zones"][1]["priority"] = "support"
        data["ppt_pages"] = [data["ppt_pages"][1]]
        data["visual_system"] = {}
        data["wayfinding_system"] = {}
        data["budget_strategies"] = []
        data["accessibility_review"] = {}
        report = validate_design_model(data, manifest(), "phase2")
        codes = {item["code"] for item in report["issues"]}
        self.assertTrue(
            {
                "ROUTE_ENDPOINT_INVALID",
                "ROUTE_DURATION_MISMATCH",
                "ZONE_FIELD_MISSING",
                "KEY_ZONE_PPT_MAPPING_MISSING",
                "VISUAL_SYSTEM_MISSING",
                "WAYFINDING_SYSTEM_MISSING",
                "BUDGET_STRATEGIES_MISSING",
                "ACCESSIBILITY_REVIEW_MISSING",
            }
            <= codes
        )

    def test_invalid_exhibit_budget_tier_and_missing_selected_story_are_blocked(self) -> None:
        data = phase2_model()
        data["selected_story"] = None
        data["exhibits"][0]["budget_tiers"] = ["premium"]
        report = validate_design_model(data, manifest(), "phase2")
        codes = {item["code"] for item in report["issues"]}
        self.assertIn("SELECTED_STORY_MISSING", codes)
        self.assertIn("BUDGET_TIER_INVALID", codes)

    def test_malformed_route_and_page_items_are_reported_without_crashing(self) -> None:
        data = phase2_model()
        data["routes"].append("not-an-object")
        data["ppt_pages"].append("not-an-object")
        report = validate_design_model(data, manifest(), "phase2")
        self.assertIn("OBJECT_INVALID", {item["code"] for item in report["issues"]})

    def test_selected_story_object_is_reported_instead_of_crashing(self) -> None:
        data = phase2_model()
        data["selected_story"] = {"id": "S01"}
        report = validate_design_model(data, manifest(), "phase2")
        self.assertIn("SELECTED_STORY_INVALID", {item["code"] for item in report["issues"]})


if __name__ == "__main__":
    unittest.main()
