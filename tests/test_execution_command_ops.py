import tempfile
import unittest

from codecortex.execution.command_ops import run_command_safe
from codecortex.execution.executor import execute_action
from codecortex.execution.models import ExecutionAction


class ExecutionCommandOpsTests(unittest.TestCase):
    def test_run_command_safe_success(self):
        with tempfile.TemporaryDirectory() as repo_path:
            result = run_command_safe(
                repo_path=repo_path,
                command=["python3", "-c", "print('hello')"],
                agent_id="cmd-agent",
                environment="test",
            )
            self.assertEqual(result.status, "success")
            self.assertEqual(result.details["returncode"], 0)
            self.assertIn("hello", result.details["stdout"])

    def test_run_command_safe_failure(self):
        with tempfile.TemporaryDirectory() as repo_path:
            result = run_command_safe(
                repo_path=repo_path,
                command=["python3", "-c", "import sys; sys.exit(3)"],
                agent_id="cmd-agent",
                environment="test",
            )
            self.assertEqual(result.status, "failure")
            self.assertEqual(result.details["error_type"], "CommandExecutionError")
            self.assertEqual(result.details["returncode"], 3)

    def test_execute_action_routes_run_command(self):
        with tempfile.TemporaryDirectory() as repo_path:
            action = ExecutionAction(
                action="run_command",
                repo=repo_path,
                agent_id="cmd-agent",
                environment="test",
                payload={"command": ["python3", "-c", "print('ok')"], "timeout_seconds": 10},
            )
            result = execute_action(action)
            self.assertEqual(result.status, "success")
            self.assertIn("ok", result.details["stdout"])


if __name__ == "__main__":
    unittest.main()
