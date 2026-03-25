import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

try:
    from cli.cortex_cli import init
    CLI_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment-dependent
    init = None
    CLI_IMPORT_ERROR = exc


@unittest.skipIf(CLI_IMPORT_ERROR is not None, f"CLI dependencies unavailable: {CLI_IMPORT_ERROR}")
class CliInitTests(unittest.TestCase):
    def test_init_creates_required_runtime_state_file(self):
        with tempfile.TemporaryDirectory() as repo_path:
            buffer = StringIO()
            with redirect_stdout(buffer):
                init(path=repo_path)

            state_path = os.path.join(repo_path, ".codecortex", "state.json")
            self.assertTrue(os.path.exists(state_path))

            with open(state_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)

            self.assertEqual(
                payload,
                {
                    "repo_initialized": True,
                    "graph_dirty": False,
                    "last_action_at": None,
                    "last_action_id": None,
                    "last_scan_at": None,
                    "last_scan_commit": None,
                },
            )

    def test_init_preserves_existing_state_file(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex"), exist_ok=True)
            state_path = os.path.join(repo_path, ".codecortex", "state.json")
            with open(state_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "repo_initialized": True,
                        "graph_dirty": True,
                        "last_action_at": "2026-03-25T00:00:00+00:00",
                        "last_action_id": "action-123",
                        "last_scan_at": "2026-03-25T00:01:00+00:00",
                        "last_scan_commit": "abc123",
                    },
                    handle,
                )

            buffer = StringIO()
            with redirect_stdout(buffer):
                init(path=repo_path)

            with open(state_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)

            self.assertTrue(payload["graph_dirty"])
            self.assertEqual(payload["last_action_id"], "action-123")

    def test_init_writes_structured_constraints_file(self):
        with tempfile.TemporaryDirectory() as repo_path:
            buffer = StringIO()
            with redirect_stdout(buffer):
                init(path=repo_path)

            constraints_path = os.path.join(repo_path, ".codecortex", "constraints.json")
            self.assertTrue(os.path.exists(constraints_path))

            with open(constraints_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)

            self.assertEqual(payload["schema_version"], "1.0")
            self.assertFalse(payload["require_fresh_graph"])
            self.assertEqual(payload["path_write_rules"][0]["pattern"], "docs/**")
            self.assertEqual(payload["command_rules"], [])
            self.assertTrue(payload["constraints"])


if __name__ == "__main__":
    unittest.main()
