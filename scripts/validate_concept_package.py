#!/usr/bin/env python3
"""Validate enterprise showroom concept deliverable packages."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PHASE1_FILES = (
    "01_需求诊断与证据台账.md",
    "02_故事线比选与确认记录.md",
)
PHASE2_FILES = PHASE1_FILES + (
    "03_企业展厅概念策划母稿.md",
    "04_PPT逐页提案脚本.md",
    "05_分区效果图提示词.md",
    "06_来源与待确认清单.md",
)
REQUIRED_SECTIONS = {
    "01_需求诊断与证据台账.md": ("## 需求诊断", "## 证据台账"),
    "02_故事线比选与确认记录.md": ("## 故事线候选", "## 确认记录"),
    "03_企业展厅概念策划母稿.md": (
        "## 项目定位",
        "## 主题与故事线",
        "## 展区规划与参观动线",
        "## 展区内容卡",
        "## 整体视觉方向",
    ),
    "04_PPT逐页提案脚本.md": ("## 页面卡",),
    "05_分区效果图提示词.md": ("## 展区提示词",),
    "06_来源与待确认清单.md": ("## 来源清单", "## 待确认问题"),
}
PLACEHOLDER_PATTERN = re.compile(
    r"\b(?:TODO|TBD|FIXME|PLACEHOLDER)\b|待补充|【[^】\n]+】|(?:示例项目|示例企业|示例科技)",
    re.IGNORECASE,
)
EMPTY_TABLE_ROW_PATTERN = re.compile(r"^\s*\|(?:\s*\|){2,}\s*$", re.MULTILINE)
OBJECT_ID_PATTERN = re.compile(r"\b(?:[ED]\d{3}|[ASZRXP]\d{2})\b")
BOUNDARY_PATTERNS = {
    "可直接施工": "不得把概念方案描述为可直接施工",
    "施工图已完成": "不得声称已经完成施工图",
    "正式预算": "不得把概念成本建议描述为正式预算",
    "精确预算": "不得输出精确预算结论",
    "工程结论": "不得输出未经专业确认的工程结论",
}
BOUNDARY_CLAUSE_SPLIT_PATTERN = re.compile(r"[，,；;。！？!?\n]+|(?:但是|但|然而|不过)")
BOUNDARY_NEGATION_PATTERN = re.compile(r"(?:不是|并非|不构成|不作为|不代表|不提供|不输出|不得|不能|禁止)")


def issue(level: str, code: str, message: str, file: str | None = None) -> dict[str, str]:
    item = {"level": level, "code": code, "message": message}
    if file:
        item["file"] = file
    return item


def find_boundary_violations(content: str) -> list[tuple[str, str]]:
    """Return affirmative boundary claims while ignoring explicit disclaimers."""
    violations: list[tuple[str, str]] = []
    for clause in BOUNDARY_CLAUSE_SPLIT_PATTERN.split(content):
        for phrase, message in BOUNDARY_PATTERNS.items():
            position = clause.find(phrase)
            if position < 0:
                continue
            if BOUNDARY_NEGATION_PATTERN.search(clause[:position]):
                continue
            violations.append((phrase, message))
    return violations


def load_optional_json(root: Path, filename: str) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    path = root / filename
    if not path.is_file():
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, issue("BLOCKER", "STRUCTURED_FILE_INVALID", f"无法解析结构化文件：{exc}", filename)
    if not isinstance(data, dict):
        return None, issue("BLOCKER", "STRUCTURED_FILE_INVALID", "结构化文件根节点必须是对象", filename)
    return data, None


def object_ids(items: Any) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {str(item.get("id")) for item in items if isinstance(item, dict) and item.get("id")}


def validate_structured_mappings(
    root: Path,
    stage: str,
    contents: dict[str, str],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    manifest, manifest_error = load_optional_json(root, "project-manifest.json")
    model, model_error = load_optional_json(root, "design-model.json")
    if manifest_error:
        issues.append(manifest_error)
    if model_error:
        issues.append(model_error)
    if manifest is None or model is None:
        issues.append(
            issue(
                "WARNING",
                "V1_COMPATIBILITY_MODE",
                "未同时发现 project-manifest.json 与 design-model.json；仅执行 V1 文件级验证",
            )
        )
        return issues

    allowed_ids = set()
    for field in ("audiences", "evidence", "design_references"):
        allowed_ids.update(object_ids(manifest.get(field)))
    for field in ("story_candidates", "routes", "zones", "exhibits", "ppt_pages"):
        allowed_ids.update(object_ids(model.get(field)))

    for filename, content in contents.items():
        for identifier in sorted(set(OBJECT_ID_PATTERN.findall(content)) - allowed_ids):
            issues.append(
                issue(
                    "BLOCKER",
                    "MARKDOWN_ID_UNKNOWN",
                    f"Markdown 引用了结构化数据中不存在的编号：{identifier}",
                    filename,
                )
            )

    story_ids = object_ids(model.get("story_candidates"))
    for identifier in sorted(story_ids):
        if identifier not in contents.get("02_故事线比选与确认记录.md", ""):
            issues.append(issue("BLOCKER", "STORY_MARKDOWN_MAPPING_MISSING", f"故事候选未进入比选文件：{identifier}", "02_故事线比选与确认记录.md"))

    if stage == "phase2":
        mapping_rules = (
            ("routes", "03_企业展厅概念策划母稿.md", "ROUTE_MARKDOWN_MAPPING_MISSING"),
            ("exhibits", "03_企业展厅概念策划母稿.md", "EXHIBIT_MARKDOWN_MAPPING_MISSING"),
            ("ppt_pages", "04_PPT逐页提案脚本.md", "PPT_PAGE_MARKDOWN_MAPPING_MISSING"),
        )
        for field, filename, code in mapping_rules:
            content = contents.get(filename, "")
            for identifier in sorted(object_ids(model.get(field))):
                if identifier not in content:
                    issues.append(issue("BLOCKER", code, f"结构化对象未进入规定交付文件：{identifier}", filename))

        key_zones = {
            str(zone.get("id"))
            for zone in model.get("zones") or []
            if isinstance(zone, dict) and zone.get("id") and zone.get("priority") == "key"
        }
        for identifier in sorted(key_zones):
            if identifier not in contents.get("03_企业展厅概念策划母稿.md", ""):
                issues.append(issue("BLOCKER", "KEY_ZONE_CONCEPT_MAPPING_MISSING", f"关键展区未进入策划母稿：{identifier}", "03_企业展厅概念策划母稿.md"))
            if identifier not in contents.get("04_PPT逐页提案脚本.md", ""):
                issues.append(issue("BLOCKER", "KEY_ZONE_PPT_MAPPING_MISSING", f"关键展区未进入 PPT 页面卡：{identifier}", "04_PPT逐页提案脚本.md"))
            if identifier not in contents.get("05_分区效果图提示词.md", ""):
                issues.append(issue("BLOCKER", "KEY_ZONE_RENDER_MAPPING_MISSING", f"关键展区缺少效果图提示词：{identifier}", "05_分区效果图提示词.md"))
    return issues


def validate_package(root: Path, stage: str) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    required_files = PHASE1_FILES if stage == "phase1" else PHASE2_FILES
    contents: dict[str, str] = {}

    if not root.is_dir():
        issues.append(issue("BLOCKER", "PACKAGE_NOT_FOUND", f"交付目录不存在：{root}"))
    else:
        for filename in required_files:
            path = root / filename
            if not path.is_file():
                issues.append(issue("BLOCKER", "MISSING_DELIVERABLE", f"缺少交付文件：{filename}", filename))
                continue
            content = path.read_text(encoding="utf-8-sig")
            contents[filename] = content
            if PLACEHOLDER_PATTERN.search(content):
                issues.append(issue("BLOCKER", "PLACEHOLDER_FOUND", "文件仍包含占位符", filename))
            if EMPTY_TABLE_ROW_PATTERN.search(content):
                issues.append(issue("BLOCKER", "EMPTY_TABLE_ROW_FOUND", "文件包含未填写的空表格行", filename))
            for _, message in find_boundary_violations(content):
                issues.append(issue("BLOCKER", "BOUNDARY_VIOLATION", message, filename))
            for heading in REQUIRED_SECTIONS[filename]:
                if heading not in content:
                    issues.append(issue("BLOCKER", "REQUIRED_SECTION_MISSING", f"缺少章节：{heading}", filename))

        if stage == "phase2":
            concept_path = root / "03_企业展厅概念策划母稿.md"
            if concept_path.is_file():
                concept = concept_path.read_text(encoding="utf-8-sig")
                if not re.search(r"\[E\d{3,}\]", concept):
                    issues.append(
                        issue(
                            "BLOCKER",
                            "EVIDENCE_REFERENCE_MISSING",
                            "策划母稿没有引用任何证据编号",
                            concept_path.name,
                        )
                    )
            prompt_path = root / "05_分区效果图提示词.md"
            if prompt_path.is_file():
                prompt_text = prompt_path.read_text(encoding="utf-8-sig")
                if not any(label in prompt_text for label in ("概念效果参考", "提案视觉", "风格探索")):
                    issues.append(
                        issue(
                            "WARNING",
                            "CONCEPT_LABEL_MISSING",
                            "效果图提示词应标明概念效果参考、提案视觉或风格探索",
                            prompt_path.name,
                        )
                    )

        issues.extend(validate_structured_mappings(root, stage, contents))

    blocker_count = sum(item["level"] == "BLOCKER" for item in issues)
    warning_count = sum(item["level"] == "WARNING" for item in issues)
    status = "FAIL" if blocker_count else ("PASS_WITH_WARNINGS" if warning_count else "PASS")
    return {
        "status": status,
        "stage": stage,
        "validator": "validate_concept_package",
        "root": str(root),
        "summary": {"blockers": blocker_count, "warnings": warning_count},
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="Deliverable directory")
    parser.add_argument("--stage", choices=("phase1", "phase2"), default="phase2")
    args = parser.parse_args()
    report = validate_package(args.package, args.stage)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
