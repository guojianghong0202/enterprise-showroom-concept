#!/usr/bin/env python3
"""Validate the structured enterprise showroom design model."""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any

try:
    from .validation_common import build_report, load_json, make_issue, valid_id
except ImportError:  # Direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from validation_common import build_report, load_json, make_issue, valid_id


STORY_DIFFERENCE_FIELDS = (
    "audience_ids",
    "proposition",
    "spatial_archetype",
    "signature_exhibit",
    "emotional_arc",
    "visual_motif",
)
EXHIBIT_REQUIRED_FIELDS = (
    "objective",
    "content",
    "media_type",
    "low_tech_fallback",
    "operations",
    "inclusion_notes",
    "budget_tiers",
)
ZONE_REQUIRED_FIELDS = ("visual_direction", "wayfinding", "render_handoff", "open_questions")
ALLOWED_BUDGET_TIERS = {"basic", "standard", "flagship"}


def blank(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def collect_ids(
    items: list[Any], prefix: str, collection: str, issues: list[dict[str, Any]]
) -> set[str]:
    found: set[str] = set()
    for index, item in enumerate(items):
        path = f"{collection}[{index}].id"
        if not isinstance(item, dict):
            issues.append(make_issue("BLOCKER", "OBJECT_INVALID", "条目必须是对象。", json_path=f"{collection}[{index}]"))
            continue
        item_id = item.get("id")
        if not valid_id(item_id, prefix):
            issues.append(
                make_issue(
                    "BLOCKER",
                    "ID_FORMAT_INVALID",
                    f"编号必须使用 {prefix} 前缀和固定两位数字：{item_id}",
                    json_path=path,
                    related_ids=[str(item_id)] if item_id else [],
                )
            )
            continue
        if item_id in found:
            issues.append(
                make_issue(
                    "BLOCKER",
                    "ID_DUPLICATE",
                    f"编号重复：{item_id}",
                    json_path=path,
                    related_ids=[item_id],
                )
            )
        found.add(item_id)
    return found


def validate_references(
    model: dict[str, Any],
    story_ids: set[str],
    zone_ids: set[str],
    route_ids: set[str],
    exhibit_ids: set[str],
    issues: list[dict[str, Any]],
) -> None:
    del route_ids  # Collected for uniqueness and future route-to-route references.
    lanes: list[tuple[str, list[dict[str, Any]], str, set[str]]] = [
        ("routes", model.get("routes") or [], "zone_ids", zone_ids),
        ("zones", model.get("zones") or [], "adjacent_to", zone_ids),
        ("zones", model.get("zones") or [], "exhibit_ids", exhibit_ids),
        ("ppt_pages", model.get("ppt_pages") or [], "zone_ids", zone_ids),
        ("ppt_pages", model.get("ppt_pages") or [], "exhibit_ids", exhibit_ids),
    ]
    for collection, items, field, allowed in lanes:
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            for reference in item.get(field) or []:
                if reference not in allowed:
                    issues.append(
                        make_issue(
                            "BLOCKER",
                            "REFERENCE_NOT_FOUND",
                            f"引用的对象不存在：{reference}",
                            json_path=f"{collection}[{index}].{field}",
                            related_ids=[str(reference)],
                        )
                    )

    for index, exhibit in enumerate(model.get("exhibits") or []):
        if not isinstance(exhibit, dict):
            continue
        zone_id = exhibit.get("zone_id")
        if zone_id not in zone_ids:
            issues.append(
                make_issue(
                    "BLOCKER",
                    "REFERENCE_NOT_FOUND",
                    f"展项引用的展区不存在：{zone_id}",
                    json_path=f"exhibits[{index}].zone_id",
                    related_ids=[str(zone_id)] if zone_id else [],
                )
            )

    selected = model.get("selected_story")
    if selected and not isinstance(selected, str):
        issues.append(
            make_issue(
                "BLOCKER",
                "SELECTED_STORY_INVALID",
                "selected_story 必须是 S## 字符串编号。",
                json_path="selected_story",
            )
        )
    elif selected and selected not in story_ids:
        issues.append(
            make_issue(
                "BLOCKER",
                "REFERENCE_NOT_FOUND",
                f"选定故事线不存在：{selected}",
                json_path="selected_story",
                related_ids=[str(selected)],
            )
        )
    for index, page in enumerate(model.get("ppt_pages") or []):
        if not isinstance(page, dict):
            continue
        story_id = page.get("story_id")
        if story_id and story_id not in story_ids:
            issues.append(
                make_issue(
                    "BLOCKER",
                    "REFERENCE_NOT_FOUND",
                    f"PPT 页面引用的故事线不存在：{story_id}",
                    json_path=f"ppt_pages[{index}].story_id",
                    related_ids=[str(story_id)],
                )
            )


def validate_story_candidates(candidates: list[Any], issues: list[dict[str, Any]]) -> None:
    if not 2 <= len(candidates) <= 3:
        issues.append(
            make_issue(
                "BLOCKER",
                "STORY_CANDIDATE_COUNT_INVALID",
                "第一阶段必须提供 2–3 条故事—空间候选。",
                json_path="story_candidates",
            )
        )
        return
    fingerprints: list[tuple[Any, ...]] = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            continue
        missing = [field for field in STORY_DIFFERENCE_FIELDS if blank(candidate.get(field))]
        if missing:
            issues.append(
                make_issue(
                    "BLOCKER",
                    "STORY_CANDIDATE_INCOMPLETE",
                    f"故事候选缺少差异化字段：{', '.join(missing)}",
                    json_path=f"story_candidates[{index}]",
                    related_ids=[candidate.get("id")] if candidate.get("id") else [],
                )
            )
        fingerprints.append(tuple(json.dumps(candidate.get(field), ensure_ascii=False, sort_keys=True) for field in STORY_DIFFERENCE_FIELDS))
    for left in range(len(fingerprints)):
        for right in range(left + 1, len(fingerprints)):
            differences = sum(a != b for a, b in zip(fingerprints[left], fingerprints[right]))
            if differences < 3:
                issues.append(
                    make_issue(
                        "BLOCKER",
                        "STORY_CANDIDATES_TOO_SIMILAR",
                        "故事候选至少应在三个专业维度上存在实质差异。",
                        json_path="story_candidates",
                    )
                )


def validate_zone_graph(zones: list[dict[str, Any]], zone_ids: set[str], issues: list[dict[str, Any]]) -> None:
    if len(zone_ids) <= 1:
        return
    graph = {zone_id: set() for zone_id in zone_ids}
    for zone in zones:
        zone_id = zone.get("id")
        if zone_id not in graph:
            continue
        for neighbor in zone.get("adjacent_to") or []:
            if neighbor in graph:
                graph[zone_id].add(neighbor)
                graph[neighbor].add(zone_id)
    start = next(iter(zone_ids))
    visited = {start}
    queue: deque[str] = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in graph[node] - visited:
            visited.add(neighbor)
            queue.append(neighbor)
    if visited != zone_ids:
        missing = sorted(zone_ids - visited)
        issues.append(
            make_issue(
                "BLOCKER",
                "ZONE_GRAPH_DISCONNECTED",
                f"展区邻接图不连通，孤立对象：{', '.join(missing)}",
                json_path="zones",
                related_ids=missing,
            )
        )


def validate_area(zones: list[dict[str, Any]], space_program: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    mode = space_program.get("allocation_mode")
    if mode == "exact":
        values = [zone.get("area_pct") for zone in zones]
        if any(not isinstance(value, (int, float)) for value in values) or abs(sum(values) - 100) > 1:
            issues.append(
                make_issue(
                    "BLOCKER",
                    "AREA_TOTAL_INVALID",
                    "精确面积比例总和必须为 100%（允许 ±1% 舍入误差）。",
                    json_path="zones",
                )
            )
    elif mode == "range":
        ranges = [zone.get("area_range_pct") or {} for zone in zones]
        if any(not isinstance(item.get("min"), (int, float)) or not isinstance(item.get("max"), (int, float)) for item in ranges):
            issues.append(make_issue("BLOCKER", "AREA_RANGE_MISSING", "每个展区都必须提供面积比例区间。", json_path="zones"))
            return
        minimum = sum(item["min"] for item in ranges)
        maximum = sum(item["max"] for item in ranges)
        if any(item["min"] > item["max"] for item in ranges) or minimum > 100 or maximum < 100:
            issues.append(
                make_issue(
                    "BLOCKER",
                    "AREA_RANGE_INVALID",
                    f"面积区间不可行：下限合计 {minimum}%，上限合计 {maximum}%。",
                    json_path="zones",
                )
            )
    else:
        issues.append(make_issue("BLOCKER", "AREA_MODE_INVALID", "面积分配模式必须为 exact 或 range。", json_path="space_program.allocation_mode"))


def validate_phase2_detail(model: dict[str, Any], manifest: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    if blank(model.get("selected_story")):
        issues.append(make_issue("BLOCKER", "SELECTED_STORY_MISSING", "第二阶段缺少已选故事线。", json_path="selected_story"))

    zones = [item for item in model.get("zones") or [] if isinstance(item, dict)]
    exhibits = [item for item in model.get("exhibits") or [] if isinstance(item, dict)]
    routes = [item for item in model.get("routes") or [] if isinstance(item, dict)]
    pages = [item for item in model.get("ppt_pages") or [] if isinstance(item, dict)]
    validate_area(zones, model.get("space_program") or {}, issues)

    confidence = (manifest.get("space") or {}).get("confidence", "unknown")
    if confidence == "low" and (model.get("space_program") or {}).get("placement_status") == "confirmed":
        issues.append(
            make_issue(
                "BLOCKER",
                "LOW_CONFIDENCE_OVERCLAIM",
                "空间置信度为 low 时不得声明确定落位。",
                json_path="space_program.placement_status",
            )
        )

    for index, zone in enumerate(zones):
        missing = [field for field in ZONE_REQUIRED_FIELDS if blank(zone.get(field))]
        if missing:
            issues.append(
                make_issue(
                    "BLOCKER",
                    "ZONE_FIELD_MISSING",
                    f"展区缺少专业设计字段：{', '.join(missing)}",
                    json_path=f"zones[{index}]",
                    related_ids=[zone.get("id")] if zone.get("id") else [],
                )
            )

    for index, exhibit in enumerate(exhibits):
        missing = [field for field in EXHIBIT_REQUIRED_FIELDS if blank(exhibit.get(field))]
        invalid_tiers = set(exhibit.get("budget_tiers") or []) - ALLOWED_BUDGET_TIERS
        if missing or invalid_tiers:
            detail = f"缺少字段：{', '.join(missing)}" if missing else f"预算档位无效：{', '.join(sorted(invalid_tiers))}"
            issues.append(
                make_issue(
                    "BLOCKER",
                    "EXHIBIT_FIELD_MISSING" if missing else "BUDGET_TIER_INVALID",
                    f"展项信息不完整，{detail}",
                    json_path=f"exhibits[{index}]",
                    related_ids=[exhibit.get("id")] if exhibit.get("id") else [],
                )
            )

    expected = (manifest.get("project") or {}).get("expected_visit_minutes") or {}
    expected_min, expected_max = expected.get("min"), expected.get("max")
    for index, route in enumerate(routes):
        duration = route.get("duration_minutes") or {}
        if isinstance(expected_min, (int, float)) and isinstance(expected_max, (int, float)):
            if duration.get("min", float("inf")) > expected_min or duration.get("max", float("-inf")) < expected_max:
                issues.append(
                    make_issue(
                        "WARNING",
                        "ROUTE_DURATION_MISMATCH",
                        "路线停留区间没有覆盖预计参观时长。",
                        json_path=f"routes[{index}].duration_minutes",
                        related_ids=[route.get("id")] if route.get("id") else [],
                    )
                )

    space = manifest.get("space") or {}
    if space.get("entrances") and space.get("exits"):
        for index, route in enumerate(routes):
            if route.get("start") not in space["entrances"] or route.get("end") not in space["exits"]:
                issues.append(
                    make_issue(
                        "BLOCKER",
                        "ROUTE_ENDPOINT_INVALID",
                        "路线起止点必须对应已知入口和出口。",
                        json_path=f"routes[{index}]",
                        related_ids=[route.get("id")] if route.get("id") else [],
                    )
                )

    key_zones = {zone.get("id") for zone in zones if zone.get("priority") == "key"}
    mapped_zones = {zone_id for page in pages for zone_id in (page.get("zone_ids") or [])}
    if missing := sorted(key_zones - mapped_zones):
        issues.append(
            make_issue(
                "BLOCKER",
                "KEY_ZONE_PPT_MAPPING_MISSING",
                f"关键展区没有映射到 PPT 页面：{', '.join(missing)}",
                json_path="ppt_pages",
                related_ids=missing,
            )
        )

    for field, code, message in (
        ("visual_system", "VISUAL_SYSTEM_MISSING", "缺少整体视觉系统。"),
        ("wayfinding_system", "WAYFINDING_SYSTEM_MISSING", "缺少导视系统。"),
        ("budget_strategies", "BUDGET_STRATEGIES_MISSING", "缺少三档概念预算策略。"),
        ("accessibility_review", "ACCESSIBILITY_REVIEW_MISSING", "缺少概念级包容性体验检查。"),
    ):
        if blank(model.get(field)):
            issues.append(make_issue("BLOCKER", code, message, json_path=field))


def validate_design_model(data: dict[str, Any], manifest: dict[str, Any] | None, stage: str) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    manifest = manifest or {}
    if data.get("schema_version") != "2.0":
        issues.append(make_issue("BLOCKER", "DESIGN_SCHEMA_INVALID", "design-model.json 必须使用 schema_version=2.0。", json_path="schema_version"))
    if data.get("phase") != stage:
        issues.append(make_issue("BLOCKER", "DESIGN_PHASE_MISMATCH", f"设计模型阶段与验证阶段不一致：{data.get('phase')} != {stage}", json_path="phase"))

    candidates = data.get("story_candidates") or []
    validate_story_candidates(candidates, issues)
    story_ids = collect_ids(candidates, "S", "story_candidates", issues)
    zones = data.get("zones") or []
    routes = data.get("routes") or []
    exhibits = data.get("exhibits") or []
    pages = data.get("ppt_pages") or []
    zone_ids = collect_ids(zones, "Z", "zones", issues)
    route_ids = collect_ids(routes, "R", "routes", issues)
    exhibit_ids = collect_ids(exhibits, "X", "exhibits", issues)
    collect_ids(pages, "P", "ppt_pages", issues)
    validate_references(data, story_ids, zone_ids, route_ids, exhibit_ids, issues)
    validate_zone_graph([item for item in zones if isinstance(item, dict)], zone_ids, issues)
    if stage == "phase2":
        validate_phase2_detail(data, manifest, issues)
    return build_report(issues, stage=stage, validator="validate_design_model")


def failure_report(code: str, message: str, stage: str) -> dict[str, Any]:
    return build_report([make_issue("BLOCKER", code, message)], stage=stage, validator="validate_design_model")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path, help="design-model.json path")
    parser.add_argument("--manifest", type=Path, help="optional project-manifest.json path")
    parser.add_argument("--stage", choices=("phase1", "phase2"), default="phase2")
    args = parser.parse_args()
    model, model_issue = load_json(args.model)
    manifest: dict[str, Any] = {}
    issues: list[dict[str, Any]] = []
    if model_issue:
        issues.append(model_issue)
    if args.manifest:
        manifest, manifest_issue = load_json(args.manifest)
        if manifest_issue:
            issues.append(manifest_issue)
            manifest = {}
    report = (
        build_report(issues, stage=args.stage, validator="validate_design_model")
        if model is None
        else validate_design_model(model, manifest, args.stage)
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
