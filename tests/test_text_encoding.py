from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".yaml", ".json", ".py"}


class TextEncodingTests(unittest.TestCase):
    def test_runtime_and_repository_text_is_utf8(self) -> None:
        failures: list[str] = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES and path.name != ".gitignore":
                continue
            try:
                path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                failures.append(str(path.relative_to(ROOT)))
        self.assertEqual(failures, [], f"非 UTF-8 文件：{failures}")


if __name__ == "__main__":
    unittest.main()
