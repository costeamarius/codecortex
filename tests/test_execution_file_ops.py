import os
import tempfile
import unittest

from codecortex.execution.errors import PathViolationError, RuntimeBypassError
from codecortex.execution.file_ops import edit_file_safe, resolve_repo_path
from codecortex.runtime.kernel import RuntimeKernel
from codecortex.runtime.models import ActionRequest


class ExecutionFileOpsTests(unittest.TestCase):
    def _write_runtime_state(self, repo_path):
        with open(
            os.path.join(repo_path, ".codecortex", "state.json"),
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(
                '{"repo_initialized": true, "graph_dirty": false, "last_action_at": null, '
                '"last_action_id": null, "last_scan_at": null, "last_scan_commit": null}'
            )

    def test_resolve_repo_path_blocks_escape(self):
        with tempfile.TemporaryDirectory() as repo_path:
            with self.assertRaises(PathViolationError):
                resolve_repo_path(repo_path, "../outside.txt")

    def test_direct_edit_file_safe_call_is_blocked(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
            file_path = os.path.join(repo_path, "config.json")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write('{"timeout": 10}\n')

            with self.assertRaises(RuntimeBypassError):
                edit_file_safe(
                    repo_path=repo_path,
                    relative_path="config.json",
                    content='{"timeout": 30}\n',
                    owner="test-agent",
                )

    def test_runtime_kernel_routes_edit_file(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
            with open(
                os.path.join(repo_path, ".codecortex", "meta.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write(
                    '{"schema_version":"1.1","repo_id":"repo-123","initialized_at":"2026-03-25T00:00:00+00:00"}'
                )
            self._write_runtime_state(repo_path)
            file_path = os.path.join(repo_path, "config.json")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write('{"timeout": 10}\n')

            result = RuntimeKernel().handle_action(
                ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    agent_id="test-agent",
                    environment="test",
                    payload={"file": "config.json", "content": '{"timeout": 30}\n', "validate": True},
                )
            )

            self.assertEqual(result.status, "success")
            self.assertIn("backup_path", result.result)
            self.assertTrue(os.path.exists(result.result["backup_path"]))
            self.assertIn("config.json", result.result["diff"])

            with open(file_path, "r", encoding="utf-8") as handle:
                self.assertIn("30", handle.read())

    def test_runtime_kernel_returns_validation_failure_for_invalid_json(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
            with open(
                os.path.join(repo_path, ".codecortex", "meta.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write(
                    '{"schema_version":"1.1","repo_id":"repo-123","initialized_at":"2026-03-25T00:00:00+00:00"}'
                )
            self._write_runtime_state(repo_path)
            file_path = os.path.join(repo_path, "config.json")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write('{"timeout": 10}\n')

            result = RuntimeKernel().handle_action(
                ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    agent_id="test-agent",
                    environment="test",
                    payload={"file": "config.json", "content": '{"timeout": }\n', "validate": True},
                )
            )

            self.assertEqual(result.status, "failure")
            self.assertEqual(result.result["error_type"], "ValidationError")
            with open(file_path, "r", encoding="utf-8") as handle:
                self.assertIn("10", handle.read())


if __name__ == "__main__":
    unittest.main()
