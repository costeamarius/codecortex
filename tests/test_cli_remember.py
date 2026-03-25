import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

try:
    from cli.cortex_cli import remember
    CLI_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment-dependent
    remember = None
    CLI_IMPORT_ERROR = exc


@unittest.skipIf(CLI_IMPORT_ERROR is not None, f"CLI dependencies unavailable: {CLI_IMPORT_ERROR}")
class CliRememberTests(unittest.TestCase):
    def test_remember_uses_decision_store(self):
        with tempfile.TemporaryDirectory() as repo_path:
            buffer = StringIO()
            with redirect_stdout(buffer):
                remember(
                    title="Use runtime kernel",
                    summary="Route actions through the runtime kernel.",
                    path=repo_path,
                )

            self.assertIn("Decision stored", buffer.getvalue())
            decisions_path = os.path.join(repo_path, ".codecortex", "decisions.jsonl")
            self.assertTrue(os.path.exists(decisions_path))
            with open(decisions_path, "r", encoding="utf-8") as handle:
                payload = json.loads(handle.readline())
            self.assertEqual(payload["title"], "Use runtime kernel")
            self.assertEqual(payload["summary"], "Route actions through the runtime kernel.")
            self.assertEqual(payload["tags"], [])
            self.assertEqual(payload["references"], [])
