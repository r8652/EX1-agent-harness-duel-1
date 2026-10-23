import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import fakes
from SDK.agent import SdkAgent

ROOT = Path(__file__).resolve().parent.parent


class PermissionsTest(unittest.TestCase):
    def test_sdk_never_passes_an_api_key_to_claude_code(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            SdkAgent(tempfile.mkdtemp(), "s1", date(2026, 10, 25))
            self.assertNotIn("ANTHROPIC_API_KEY", os.environ)

    def test_api_main_stops_without_key(self):
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        out = Path(tempfile.mkdtemp()) / "api.json"
        proc = subprocess.run([sys.executable, str(ROOT / "API" / "main.py"), "--scenario",
                               str(ROOT / "scenario.json"), "--out", str(out)],
                              env=env, capture_output=True, text=True, timeout=60)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("ANTHROPIC_API_KEY is not set", proc.stderr)
        self.assertFalse(out.exists())

    def test_no_key_in_source(self):
        for path in ROOT.rglob("*"):
            if path.suffix in (".py", ".json", ".md", ".txt") and "state" not in path.parts:
                text = path.read_text(encoding="utf-8")
                self.assertNotRegex(text, r"sk-ant-(api|admin)\d\d-", str(path))


if __name__ == "__main__":
    unittest.main()
