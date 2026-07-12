#!/usr/bin/env python3
"""Validate enterprise showroom concept input manifests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ALLOWED_SOURCE_TYPES = {
    "user_formal_material",
    "company_official",
    "official_wechat",
    "annual_report",
    "government",
    "industry_association",
}
ALLOWED_EVIDENCE_STATUSES = {"已核实", "用户提供待核实", "来源冲突", "缺少来源"}


def issue(level: str, code: str, message: str, path: str | None = None) -> dict[str, str]:
    item = {"level": level, "code": code, "message": message}
    if path:
        item["path"] = path
    return item


def is_blank(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def validate_manifest(data: dict[str, Any], stage: str) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    project = data.get("project") or {}

    required_project_fields = {
        "name": "项目名称",
        "company_name": "企业名称",
        "objective": "建设目标",
        "audiences": "核心受众",
    }
    for field, label in required_project_fields.items():
        if is_blank(project.get(field)):
            issues.append(issue("BLOCKER", "PROJECT_FIELD_MISSING", f"缺少{label}", f"project.{field}"))

    if is_blank(data.get("brand_materials")):
        issues.append(issue("BLOCKER", "BRAND_MATERIALS_MISSING", "至少需要一项企业品牌资料", "brand_materials"))

    space = data.get("space") or {}
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
        evidence_id = item.get("id")
        if is_blank(evidence_id):
            issues.append(issue("BLOCKER", "EVIDENCE_ID_MISSING", "证据条目缺少编号", f"{item_path}.id"))
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

    blocker_count = sum(item["level"] == "BLOCKER" for item in issues)
    warning_count = sum(item["level"] == "WARNING" for item in issues)
    status = "FAIL" if blocker_count else ("PASS_WITH_WARNINGS" if warning_count else "PASS")
    return {
        "status": status,
        "stage": stage,
        "summary": {"blockers": blocker_count, "warnings": warning_count},
        "issues": issues,
    }


def failure_report(code: str, message: str, stage: str) -> dict[str, Any]:
    return {
        "status": "FAIL",
        "stage": stage,
        "summary": {"blockers": 1, "warnings": 0},
        "issues": [issue("BLOCKER", code, message)],
    }


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
