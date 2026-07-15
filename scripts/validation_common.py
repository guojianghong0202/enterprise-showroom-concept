#!/usr/bin/env python3
"""Shared helpers for enterprise showroom V2 validators."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable


VALIDATOR_VERSION = "2.0.0"
ID_WIDTHS = {"A": 2, "E": 3, "D": 3, "S": 2, "Z": 2, "R": 2, "X": 2, "P": 2}


def make_issue(
    level: str,
    code: str,
    message: str,
    *,
    file: str | None = None,
    json_path: str | None = None,
    related_ids: Iterable[str] | None = None,
    impact: str | None = None,
    suggested_fix: str | None = None,
) -> dict[str, Any]:
    """Create a stable machine-readable issue object."""
    return {
        "level": level,
        "code": code,
        "message": message,
        "file": file,
        "json_path": json_path,
        "related_ids": list(related_ids or []),
        "impact": impact,
        "suggested_fix": suggested_fix,
    }


def summarize_issues(issues: Iterable[dict[str, Any]]) -> dict[str, int]:
    materialized = list(issues)
    return {
        "blockers": sum(item.get("level") == "BLOCKER" for item in materialized),
        "warnings": sum(item.get("level") == "WARNING" for item in materialized),
    }


def status_from_summary(summary: dict[str, int]) -> str:
    if summary["blockers"]:
        return "FAIL"
    if summary["warnings"]:
        return "PASS_WITH_WARNINGS"
    return "PASS"


def build_report(
    issues: list[dict[str, Any]],
    *,
    stage: str,
    validator: str,
    **extra: Any,
) -> dict[str, Any]:
    summary = summarize_issues(issues)
    report: dict[str, Any] = {
        "status": status_from_summary(summary),
        "stage": stage,
        "validator": validator,
        "validator_version": VALIDATOR_VERSION,
        "summary": summary,
        "issues": issues,
    }
    report.update(extra)
    return report


def valid_id(value: Any, prefix: str) -> bool:
    width = ID_WIDTHS.get(prefix)
    return bool(width and isinstance(value, str) and re.fullmatch(rf"{re.escape(prefix)}\d{{{width}}}", value))


def load_json(path: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Read a UTF-8 JSON object and return either data or a structured issue."""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return None, make_issue(
            "BLOCKER",
            "JSON_FILE_NOT_FOUND",
            f"找不到 JSON 文件：{path.name}",
            file=path.name,
            suggested_fix="创建或恢复该结构化文件后重新验证。",
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, make_issue(
            "BLOCKER",
            "JSON_FILE_INVALID",
            f"无法按 UTF-8 JSON 解析：{exc}",
            file=path.name,
            suggested_fix="保存为 UTF-8 编码并修复 JSON 语法。",
        )
    if not isinstance(data, dict):
        return None, make_issue(
            "BLOCKER",
            "JSON_ROOT_INVALID",
            "JSON 根节点必须是对象。",
            file=path.name,
        )
    return data, None


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
