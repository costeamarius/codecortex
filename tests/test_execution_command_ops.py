import os
import tempfile
import unittest

from codecortex.execution.errors import RuntimeBypassError
from codecortex.execution.command_ops import run_command_safe
from codecortex.runtime.kernel import RuntimeKernel
from codecortex.runtime.models import ActionRequest


class ExecutionCommandOpsTests(unittest.TestCase):
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

    def test_direct_run_command_safe_call_is_blocked(self):
        with tempfile.TemporaryDirectory() as repo_path:
            with self.assertRaises(RuntimeBypassError):
                run_command_safe(
                    repo_path=repo_path,
                    command=["python3", "-c", "print('hello')"],
                    agent_id="cmd-agent",
                    environment="test",
                )

    def test_runtime_kernel_routes_run_command_success(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex"), exist_ok=True)
            with open(
                os.path.join(repo_path, ".codecortex", "meta.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write(
                    '{"schema_version":"1.1","repo_id":"repo-123","initialized_at":"2026-03-25T00:00:00+00:00"}'
                )
            self._write_runtime_state(repo_path)
            result = RuntimeKernel().handle_action(
                ActionRequest(
                    action="run_command",
                    repo=repo_path,
                    agent_id="cmd-agent",
                    environment="test",
                    payload={"command": ["python3", "-c", "print('hello')"], "timeout_seconds": 10},
                )
            )
            self.assertEqual(result.status, "success")
            self.assertIn("hello", result.result["stdout"])

    def test_runtime_kernel_routes_run_command_failure(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex"), exist_ok=True)
            with open(os.path.join(repo_path, ".codecortex", "meta.json"), "w", encoding="utf-8") as handle:
                handle.write(
                    '{"schema_version":"1.1","repo_id":"repo-123","initialized_at":"2026-03-25T00:00:00+00:00"}'
                )
            self._write_runtime_state(repo_path)

            result = RuntimeKernel().handle_action(
                ActionRequest(
                    action="run_command",
                    repo=repo_path,
                    agent_id="cmd-agent",
                    environment="test",
                    payload={"command": ["python3", "-c", "import sys; sys.exit(3)"], "timeout_seconds": 10},
                )
            )
            self.assertEqual(result.status, "failure")
            self.assertEqual(result.result["error_type"], "CommandExecutionError")
            self.assertEqual(result.result["returncode"], 3)


if __name__ == "__main__":
    unittest.main()
