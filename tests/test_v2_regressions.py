import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_concept_package.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_concept_package", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_validator()


class FakeFile:
    def __init__(self, name: str, content: str | None):
        self.name = name
        self._content = content

    def is_file(self) -> bool:
        return self._content is not None

    def read_text(self, encoding: str) -> str:
        if self._content is None:
            raise FileNotFoundError(self.name)
        return self._content


class FakeRoot:
    def __init__(self, files: dict[str, str]):
        self.files = files

    def is_dir(self) -> bool:
        return True

    def __truediv__(self, name: str) -> FakeFile:
        return FakeFile(name, self.files.get(name))

    def __str__(self) -> str:
        return "<memory-package>"


def complete_phase2_files() -> dict[str, str]:
    return {
        "01_需求诊断与证据台账.md": "## 需求诊断\n内容\n## 证据台账\n[E001]\n",
        "02_故事线比选与确认记录.md": "## 故事线候选\nS01\n## 确认记录\n已确认\n",
        "03_企业展厅概念策划母稿.md": (
            "## 项目定位\n[E001]\n"
            "## 主题与故事线\nS01\n"
            "## 展区规划与参观动线\nZ01\n"
            "## 展区内容卡\nZ01\n"
            "## 整体视觉方向\n品牌视觉\n"
        ),
        "04_PPT逐页提案脚本.md": "## 页面卡\nP01\n",
        "05_分区效果图提示词.md": "## 展区提示词\n概念效果参考\n",
        "06_来源与待确认清单.md": "## 来源清单\n[E001]\n## 待确认问题\n无\n",
    }


def issue_codes(report: dict) -> set[str]:
    return {item["code"] for item in report["issues"]}


class V2RegressionTests(unittest.TestCase):
    def test_openai_yaml_is_utf8(self) -> None:
        content = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("企业品牌展厅", content)

    def test_negative_disclaimer_is_not_a_boundary_violation(self) -> None:
        files = complete_phase2_files()
        files["03_企业展厅概念策划母稿.md"] += "\n本文件不是施工图、正式预算或工程结论。\n"

        report = VALIDATOR.validate_package(FakeRoot(files), "phase2")

        self.assertNotIn("BOUNDARY_VIOLATION", issue_codes(report))

    def test_chinese_bracket_placeholder_is_blocked(self) -> None:
        files = complete_phase2_files()
        files["03_企业展厅概念策划母稿.md"] += "\n## 设计说明\n【填写设计说明】\n"

        report = VALIDATOR.validate_package(FakeRoot(files), "phase2")

        self.assertIn("PLACEHOLDER_FOUND", issue_codes(report))


if __name__ == "__main__":
    unittest.main()
