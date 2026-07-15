#!/usr/bin/env python3
"""Run all V2 enterprise showroom validators and write one report."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .validate_concept_package import validate_package
    from .validate_design_model import validate_design_model
    from .validate_input_manifest import normalize_manifest, validate_manifest
    from .validation_common import VALIDATOR_VERSION, load_json, status_from_summary, summarize_issues, write_json
except ImportError:  # Direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from validate_concept_package import validate_package
    from validate_design_model import validate_design_model
    from validate_input_manifest import normalize_manifest, validate_manifest
    from validation_common import VALIDATOR_VERSION, load_json, status_from_summary, summarize_issues, write_json


def aggregate_reports(reports: list[dict[str, Any]], *, stage: str, adapters: list[str] | None = None) -> dict[str, Any]:
    issues = [item for report in reports for item in report.get("issues", [])]
    summary = summarize_issues(issues)
    status = status_from_summary(summary)
    score = max(0, 100 - summary["blockers"] * 10 - summary["warnings"] * 2)
    final_status = "概念提案可用" if status != "FAIL" and score >= 80 else ("需修正后复验" if status == "FAIL" else "可用但需复核")
    return {
        "status": status,
        "final_status": final_status,
        "stage": stage,
        "quality_score": score,
        "summary": summary,
        "degradation_reasons": [item["message"] for item in issues if item.get("level") == "WARNING"],
        "adapters": adapters or ["generic"],
        "validator_version": VALIDATOR_VERSION,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "validators": [report.get("validator", "validate_concept_package") for report in reports],
        "issues": issues,
    }


def validate_project(root: Path, stage: str) -> dict[str, Any]:
    manifest, manifest_error = load_json(root / "project-manifest.json")
    model, model_error = load_json(root / "design-model.json")
    reports: list[dict[str, Any]] = []
    adapters = ["generic"]
    if manifest_error:
        reports.append({"validator": "validate_input_manifest", "issues": [manifest_error]})
    elif manifest is not None:
        reports.append(validate_manifest(manifest, stage))
        normalized, _ = normalize_manifest(manifest)
        adapters = (normalized.get("project") or {}).get("adapters") or ["generic"]
    if model_error:
        reports.append({"validator": "validate_design_model", "issues": [model_error]})
    elif model is not None:
        reports.append(validate_design_model(model, manifest or {}, stage))
    reports.append(validate_package(root, stage))
    return aggregate_reports(reports, stage=stage, adapters=adapters)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="成果目录")
    parser.add_argument("--stage", choices=("phase1", "phase2"), default="phase2")
    parser.add_argument("--no-write", action="store_true", help="只打印报告，不写 validation-report.json")
    args = parser.parse_args()
    report = validate_project(args.package, args.stage)
    if not args.no_write and args.package.is_dir():
        write_json(args.package / "validation-report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
