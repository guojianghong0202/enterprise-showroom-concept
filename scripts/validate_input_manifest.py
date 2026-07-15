#!/usr/bin/env python3
"""Validate enterprise showroom concept input manifests."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

try:
    from .validation_common import build_report, make_issue, valid_id
except ImportError:  # Direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from validation_common import build_report, make_issue, valid_id


ALLOWED_SOURCE_TYPES = {
    "user_formal_material",
    "company_official",
    "official_wechat",
    "annual_report",
    "government",
    "industry_association",
}
ALLOWED_EVIDENCE_STATUSES = {"已核实", "用户提供待核实", "来源冲突", "缺少来源"}
ALLOWED_DESIGN_SOURCE_TYPES = {
    "design_firm_official",
    "design_award",
    "professional_association",
    "government_standard",
    "public_cultural_institution",
    "manufacturer_technical",
}
ALLOWED_SPACE_CONFIDENCE = {"high", "medium", "low", "unknown"}
ALLOWED_BUDGET_TIERS = {"basic", "standard", "flagship", "unknown"}
ROOT_DEFAULTS: dict[str, Any] = {
    "audiences": [],
    "brand_materials": [],
    "space": {},
    "constraints": [],
    "storyline": {
        "confirmed": False,
        "selected_id": None,
        "confirmed_at": None,
        "confirmation_note": None,
    },
    "evidence": [],
    "design_references": [],
    "conflicts": [],
    "assumptions": [],
    "open_questions": [],
}


def issue(level: str, code: str, message: str, path: str | None = None) -> dict[str, Any]:
    """Compatibility wrapper for the V1 validator API."""
    item = make_issue(level, code, message, file="project-manifest.json", json_path=path)
    if path:
        item["path"] = path
    return item


def is_blank(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def normalize_manifest(data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Normalize V1 manifests to V2 in memory without modifying the caller's data."""
    normalized = copy.deepcopy(data)
    warnings: list[dict[str, Any]] = []
    is_v2 = normalized.get("schema_version") == "2.0"
    if not is_v2:
        warnings.append(
            issue(
                "WARNING",
                "V1_MANIFEST_NORMALIZED",
                "旧版 manifest 已在内存中规范化为 V2；未提供的新字段保持 unknown 或空值。",
                "schema_version",
            )
        )
        normalized["schema_version"] = "2.0"

    project = normalized.setdefault("project", {})
    if not isinstance(project, dict):
        project = {}
        normalized["project"] = project
    legacy_audiences = project.pop("audiences", None) if not is_v2 else None
    if "audiences" not in normalized and legacy_audiences:
        normalized["audiences"] = [
            item
            if isinstance(item, dict)
            else {
                "id": f"A{index:02d}",
                "name": str(item),
                "scenario": "unknown",
                "core_question": "unknown",
                "leave_memory": "unknown",
                "desired_action": "unknown",
            }
            for index, item in enumerate(legacy_audiences, start=1)
        ]
    for field, default in ROOT_DEFAULTS.items():
        normalized.setdefault(field, copy.deepcopy(default))
    space = normalized.get("space")
    if not isinstance(space, dict):
        normalized["space"] = {}
    normalized["space"].setdefault("confidence", "unknown")
    project.setdefault("budget_tier", "unknown")
    project.setdefault("adapters", ["generic"])
    return normalized, warnings


def validate_manifest(data: dict[str, Any], stage: str) -> dict[str, Any]:
    data, normalization_issues = normalize_manifest(data)
    issues: list[dict[str, Any]] = list(normalization_issues)
    project = data.get("project") or {}

    required_project_fields = {
        "name": "项目名称",
        "company_name": "企业名称",
        "objective": "建设目标",
    }
    for field, label in required_project_fields.items():
        if is_blank(project.get(field)):
            issues.append(issue("BLOCKER", "PROJECT_FIELD_MISSING", f"缺少{label}", f"project.{field}"))

    audiences = data.get("audiences") or []
    if not audiences:
        issues.append(issue("BLOCKER", "AUDIENCES_MISSING", "至少需要一类核心受众", "audiences"))
    audience_ids: set[str] = set()
    for index, audience in enumerate(audiences):
        path = f"audiences[{index}]"
        if not isinstance(audience, dict):
            issues.append(issue("BLOCKER", "AUDIENCE_INVALID", "受众条目必须是对象", path))
            continue
        audience_id = audience.get("id")
        if not valid_id(audience_id, "A"):
            issues.append(issue("BLOCKER", "AUDIENCE_ID_INVALID", f"无效受众编号：{audience_id}", f"{path}.id"))
        elif audience_id in audience_ids:
            issues.append(issue("BLOCKER", "AUDIENCE_ID_DUPLICATE", f"受众编号重复：{audience_id}", f"{path}.id"))
        else:
            audience_ids.add(audience_id)
        if is_blank(audience.get("name")):
            issues.append(issue("BLOCKER", "AUDIENCE_NAME_MISSING", "受众缺少名称", f"{path}.name"))

    if project.get("budget_tier", "unknown") not in ALLOWED_BUDGET_TIERS:
        issues.append(issue("BLOCKER", "BUDGET_TIER_INVALID", "预算档位必须为 basic、standard、flagship 或 unknown", "project.budget_tier"))
    adapters = project.get("adapters") or []
    if len(adapters) > 2:
        issues.append(issue("BLOCKER", "ADAPTER_COUNT_INVALID", "最多组合两个行业适配器", "project.adapters"))

    if is_blank(data.get("brand_materials")):
        issues.append(issue("BLOCKER", "BRAND_MATERIALS_MISSING", "至少需要一项企业品牌资料", "brand_materials"))

    space = data.get("space") or {}
    if space.get("confidence", "unknown") not in ALLOWED_SPACE_CONFIDENCE:
        issues.append(issue("BLOCKER", "SPACE_CONFIDENCE_INVALID", "空间置信度必须为 high、medium、low 或 unknown", "space.confidence"))
    if is_blank(space.get("area_sqm")) or is_blank(space.get("ceiling_height_m")):
        issues.append(
            issue(
                "WARNING",
                "SPACE_DIMENSIONS_MISSING",
                "缺少面积或层高，只能输出展区关系与面积分配原则",
                "space",
            )
        )
    if is_blank(space.get("floor_plan")):
        issues.append(issue("WARNING", "FLOOR_PLAN_MISSING", "缺少平面图，不能判断具体空间落位", "space.floor_plan"))
    if is_blank(space.get("entrances")) or is_blank(space.get("exits")):
        issues.append(
            issue(
                "WARNING",
                "ACCESS_POINTS_MISSING",
                "缺少出入口信息，只能输出候选参观动线",
                "space.entrances",
            )
        )

    evidence = data.get("evidence") or []
    if not evidence:
        level = "BLOCKER" if stage == "phase2" else "WARNING"
        issues.append(issue(level, "EVIDENCE_MISSING", "尚未建立企业事实证据台账", "evidence"))

    conflict_evidence_found = False
    evidence_ids: set[str] = set()
    for index, item in enumerate(evidence):
        item_path = f"evidence[{index}]"
        if not isinstance(item, dict):
            issues.append(issue("BLOCKER", "EVIDENCE_INVALID", "企业事实证据条目必须是对象", item_path))
            continue
        evidence_id = item.get("id")
        if is_blank(evidence_id):
            issues.append(issue("BLOCKER", "EVIDENCE_ID_MISSING", "证据条目缺少编号", f"{item_path}.id"))
        elif not valid_id(evidence_id, "E"):
            issues.append(issue("BLOCKER", "EVIDENCE_ID_INVALID", f"企业事实证据必须使用 E###：{evidence_id}", f"{item_path}.id"))
        elif evidence_id in evidence_ids:
            issues.append(issue("BLOCKER", "EVIDENCE_ID_DUPLICATE", f"证据编号重复：{evidence_id}", f"{item_path}.id"))
        else:
            evidence_ids.add(str(evidence_id))

        source_type = item.get("source_type")
        if source_type not in ALLOWED_SOURCE_TYPES:
            issues.append(
                issue(
                    "BLOCKER",
                    "SOURCE_TYPE_NOT_ALLOWED",
                    f"不允许使用该来源类型：{source_type}",
                    f"{item_path}.source_type",
                )
            )

        status = item.get("status")
        if status not in ALLOWED_EVIDENCE_STATUSES:
            issues.append(issue("BLOCKER", "EVIDENCE_STATUS_INVALID", f"无效证据状态：{status}", f"{item_path}.status"))
        if status == "来源冲突":
            conflict_evidence_found = True
        if is_blank(item.get("claim")) or is_blank(item.get("source")):
            issues.append(issue("BLOCKER", "EVIDENCE_CONTENT_MISSING", "证据缺少事实表述或来源", item_path))
        if is_blank(item.get("locator")):
            issues.append(issue("WARNING", "EVIDENCE_LOCATOR_MISSING", "证据缺少页码、章节或网页定位", f"{item_path}.locator"))

    if conflict_evidence_found and is_blank(data.get("conflicts")):
        issues.append(
            issue(
                "BLOCKER",
                "CONFLICT_RECORD_MISSING",
                "存在来源冲突，但未建立待核实冲突记录",
                "conflicts",
            )
        )

    design_ids: set[str] = set()
    for index, item in enumerate(data.get("design_references") or []):
        item_path = f"design_references[{index}]"
        if not isinstance(item, dict):
            issues.append(issue("BLOCKER", "DESIGN_REFERENCE_INVALID", "设计参考条目必须是对象", item_path))
            continue
        reference_id = item.get("id")
        if not valid_id(reference_id, "D"):
            issues.append(issue("BLOCKER", "DESIGN_REFERENCE_ID_INVALID", f"设计参考必须使用 D###：{reference_id}", f"{item_path}.id"))
        elif reference_id in design_ids:
            issues.append(issue("BLOCKER", "DESIGN_REFERENCE_ID_DUPLICATE", f"设计参考编号重复：{reference_id}", f"{item_path}.id"))
        else:
            design_ids.add(reference_id)
        if item.get("source_type") not in ALLOWED_DESIGN_SOURCE_TYPES:
            issues.append(issue("BLOCKER", "DESIGN_SOURCE_TYPE_NOT_ALLOWED", f"不允许使用该设计参考来源类型：{item.get('source_type')}", f"{item_path}.source_type"))
        if any(is_blank(item.get(field)) for field in ("source", "purpose", "takeaway", "limitations")):
            issues.append(issue("BLOCKER", "DESIGN_REFERENCE_CONTENT_MISSING", "设计参考缺少来源、用途、借鉴点或不适用条件", item_path))

    if stage == "phase2":
        storyline = data.get("storyline") or {}
        if storyline.get("confirmed") is not True or is_blank(storyline.get("selected_id")):
            issues.append(
                issue(
                    "BLOCKER",
                    "STORYLINE_NOT_CONFIRMED",
                    "第二阶段必须先确认故事线及其编号",
                    "storyline",
                )
            )
        elif is_blank(storyline.get("confirmed_at")) or is_blank(storyline.get("confirmation_note")):
            issues.append(
                issue(
                    "BLOCKER",
                    "STORYLINE_CONFIRMATION_INCOMPLETE",
                    "第二阶段必须记录确认时间和确认说明",
                    "storyline",
                )
            )

    return build_report(issues, stage=stage, validator="validate_input_manifest", normalized_schema="2.0")


def failure_report(code: str, message: str, stage: str) -> dict[str, Any]:
    return build_report([issue("BLOCKER", code, message)], stage=stage, validator="validate_input_manifest")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="UTF-8 JSON manifest")
    parser.add_argument("--stage", choices=("phase1", "phase2"), default="phase1")
    args = parser.parse_args()

    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        report = failure_report("MANIFEST_NOT_FOUND", f"找不到清单：{args.manifest}", args.stage)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        report = failure_report("MANIFEST_INVALID", f"无法解析 JSON 清单：{exc}", args.stage)
    else:
        if not isinstance(data, dict):
            report = failure_report("MANIFEST_INVALID", "清单根节点必须是 JSON 对象", args.stage)
        else:
            report = validate_manifest(data, args.stage)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
