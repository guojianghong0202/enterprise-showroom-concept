#!/usr/bin/env python3
"""Initialize a non-overwriting enterprise showroom V2 project package."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from .validation_common import load_json, write_json
except ImportError:  # Direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from validation_common import load_json, write_json


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
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
ASSET_BY_DELIVERABLE = {
    "01_需求诊断与证据台账.md": "diagnosis-template.md",
    "02_故事线比选与确认记录.md": "story-comparison-template.md",
    "03_企业展厅概念策划母稿.md": "concept-document-template.md",
    "04_PPT逐页提案脚本.md": "ppt-page-script-template.md",
    "05_分区效果图提示词.md": "render-prompt-template.md",
    "06_来源与待确认清单.md": "sources-and-open-questions-template.md",
}


def phase_file_names(stage: str) -> tuple[str, ...]:
    return PHASE1_FILES if stage == "phase1" else PHASE2_FILES


def load_template(name: str) -> dict[str, Any]:
    return json.loads((ASSETS / name).read_text(encoding="utf-8"))


def project_slug(value: str) -> str:
    ascii_slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if ascii_slug:
        return ascii_slug
    return "showroom-" + "".join(f"{ord(char):x}" for char in value[:8])


def build_initial_manifest(project_name: str, company_name: str) -> dict[str, Any]:
    manifest = copy.deepcopy(load_template("project-manifest-template.json"))
    manifest["project"]["id"] = project_slug(project_name)
    manifest["project"]["name"] = project_name
    manifest["project"]["company_name"] = company_name
    return manifest


def directory_has_content(path: Path) -> bool:
    return path.exists() and any(path.iterdir())


def versioned_target(base: Path) -> Path:
    if not directory_has_content(base):
        return base
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = base.with_name(f"{base.name}-v{stamp}")
    suffix = 2
    while candidate.exists():
        candidate = base.with_name(f"{base.name}-v{stamp}-{suffix:02d}")
        suffix += 1
    return candidate


def write_markdown_skeletons(target: Path, stage: str) -> None:
    for filename in phase_file_names(stage):
        path = target / filename
        if path.exists():
            continue
        asset = ASSETS / ASSET_BY_DELIVERABLE[filename]
        if not asset.is_file():
            raise FileNotFoundError(f"缺少交付模板：{asset.name}")
        path.write_text(asset.read_text(encoding="utf-8"), encoding="utf-8")


def initialize_phase1(output: Path, project_name: str, company_name: str) -> Path:
    target = versioned_target(output / project_name)
    target.mkdir(parents=True, exist_ok=True)
    manifest = build_initial_manifest(project_name, company_name)
    model = load_template("design-model-template.json")
    model["project_id"] = manifest["project"]["id"]
    report = load_template("validation-report-template.json")
    write_json(target / "project-manifest.json", manifest)
    write_json(target / "design-model.json", model)
    write_json(target / "validation-report.json", report)
    write_markdown_skeletons(target, "phase1")
    return target


def initialize_phase2(project_dir: Path) -> Path:
    manifest, error = load_json(project_dir / "project-manifest.json")
    if error or manifest is None:
        raise ValueError(error["message"] if error else "缺少 project-manifest.json")
    storyline = manifest.get("storyline") or {}
    if not all((storyline.get("confirmed") is True, storyline.get("selected_id"), storyline.get("confirmed_at"), storyline.get("confirmation_note"))):
        raise ValueError("第二阶段需要完整的故事线确认记录。")
    model, model_error = load_json(project_dir / "design-model.json")
    if model_error or model is None:
        raise ValueError(model_error["message"] if model_error else "缺少 design-model.json")
    if model.get("phase") != "phase2":
        model["phase"] = "phase2"
        model["selected_story"] = storyline["selected_id"]
        write_json(project_dir / "design-model.json", model)
    write_markdown_skeletons(project_dir, "phase2")
    return project_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-name", help="项目名称；phase1 必填")
    parser.add_argument("--company-name", help="企业名称；phase1 必填")
    parser.add_argument("--output", type=Path, required=True, help="phase1 为成果父目录；phase2 为既有项目目录")
    parser.add_argument("--stage", choices=("phase1", "phase2"), default="phase1")
    args = parser.parse_args()
    try:
        if args.stage == "phase1":
            if not args.project_name or not args.company_name:
                parser.error("phase1 必须同时提供 --project-name 和 --company-name")
            target = initialize_phase1(args.output, args.project_name, args.company_name)
        else:
            target = initialize_phase2(args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "message": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"status": "CREATED", "stage": args.stage, "project_dir": str(target)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
