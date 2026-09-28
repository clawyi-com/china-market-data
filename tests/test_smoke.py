"""Offline smoke tests for the distributed skill bundle."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.0.4"


def frontmatter() -> str:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    opening, metadata, _body = text.split("---", 2)
    if opening.strip():
        raise AssertionError("SKILL.md must start with YAML frontmatter")
    return metadata


def scalar(metadata: str, key: str) -> str:
    match = re.search(rf"^\s*{re.escape(key)}:\s*[\"']?([^\"'\n]+)", metadata, re.MULTILINE)
    if not match:
        raise AssertionError(f"Missing frontmatter key: {key}")
    return match.group(1).strip()


class SkillSmokeTests(unittest.TestCase):
    def test_frontmatter_matches_agent_skills_spec(self):
        metadata = frontmatter()
        self.assertEqual(scalar(metadata, "name"), "china-market-data")
        description = scalar(metadata, "description")
        self.assertGreater(len(description), 0)
        self.assertLessEqual(len(description), 1024)
        self.assertLessEqual(len(scalar(metadata, "compatibility")), 500)
        self.assertEqual(scalar(metadata, "license"), "Apache-2.0")

    def test_versions_are_consistent(self):
        metadata = frontmatter()
        self.assertEqual(scalar(metadata, "version"), VERSION)
        package_metadata = json.loads((ROOT / ".meta.json").read_text(encoding="utf-8"))
        self.assertEqual(package_metadata["version"], VERSION)
        citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        self.assertRegex(citation, rf"(?m)^version:\s*{re.escape(VERSION)}$")

    def test_standard_library_quote_cli_help(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/tencent_quote.py"), "--help"],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("批量查询腾讯实时行情", result.stdout)

    def test_setup_cli_help(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/setup_env.py"), "--help"],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--check-only", result.stdout)

    def test_release_archive_is_complete(self):
        from tools.build_release import build

        archive = build(ROOT)
        with zipfile.ZipFile(archive) as bundle:
            self.assertIsNone(bundle.testzip())
            names = set(bundle.namelist())
        required = {
            "china-market-data/.meta.json",
            "china-market-data/SKILL.md",
            "china-market-data/requirements.txt",
            "china-market-data/scripts/tencent_quote.py",
            "china-market-data/references/quotes-and-kline.md",
            "china-market-data/tools/setup_env.py",
            "china-market-data/CITATION.cff",
        }
        self.assertTrue(required <= names, required - names)


if __name__ == "__main__":
    unittest.main()
