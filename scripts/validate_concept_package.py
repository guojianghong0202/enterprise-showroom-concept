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
PLACEHOLDER_PATTERN = re.compile(r"\b(?:TODO|TBD|FIXME|PLACEHOLDER)\b|待补充", re.IGNORECASE)
BOUNDARY_PATTERNS = {
    "可直接施工": "不得把概念方案描述为可直接施工",
    "施工图已完成": "不得声称已经完成施工图",
    "正式预算": "不得把概念成本建议描述为正式预算",
    "精确预算": "不得输出精确预算结论",
    "工程结论": "不得输出未经专业确认的工程结论",
}


def issue(level: str, code: str, message: str, file: str | None = None) -> dict[str, str]:
    item = {"level": level, "code": code, "message": message}
    if file:
        item["file"] = file
    return item


def validate_package(root: Path, stage: str) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    required_files = PHASE1_FILES if stage == "phase1" else PHASE2_FILES

    if not root.is_dir():
        issues.append(issue("BLOCKER", "PACKAGE_NOT_FOUND", f"交付目录不存在：{root}"))
    else:
        for filename in required_files:
            path = root / filename
            if not path.is_file():
                issues.append(issue("BLOCKER", "MISSING_DELIVERABLE", f"缺少交付文件：{filename}", filename))
                continue
            content = path.read_text(encoding="utf-8-sig")
            if PLACEHOLDER_PATTERN.search(content):
                issues.append(issue("BLOCKER", "PLACEHOLDER_FOUND", "文件仍包含占位符", filename))
            for phrase, message in BOUNDARY_PATTERNS.items():
                if phrase in content:
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

    blocker_count = sum(item["level"] == "BLOCKER" for item in issues)
    warning_count = sum(item["level"] == "WARNING" for item in issues)
    status = "FAIL" if blocker_count else ("PASS_WITH_WARNINGS" if warning_count else "PASS")
    return {
        "status": status,
        "stage": stage,
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
