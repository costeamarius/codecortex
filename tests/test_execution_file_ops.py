import os
import tempfile
import unittest

from codecortex.execution.file_ops import edit_file_safe, resolve_repo_path
from codecortex.execution.models import ExecutionAction
from codecortex.execution.executor import execute_action
from codecortex.execution.errors import PathViolationError


class ExecutionFileOpsTests(unittest.TestCase):
    def test_resolve_repo_path_blocks_escape(self):
        with tempfile.TemporaryDirectory() as repo_path:
            with self.assertRaises(PathViolationError):
                resolve_repo_path(repo_path, "../outside.txt")

    def test_edit_file_safe_writes_backup_and_returns_diff(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
            file_path = os.path.join(repo_path, "config.json")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write('{"timeout": 10}\n')

            result = edit_file_safe(
                repo_path=repo_path,
                relative_path="config.json",
                content='{"timeout": 30}\n',
                owner="test-agent",
            )

            self.assertEqual(result.status, "success")
            self.assertIn("backup_path", result.details)
            self.assertTrue(os.path.exists(result.details["backup_path"]))
            self.assertIn("config.json", result.details["diff"])

            with open(file_path, "r", encoding="utf-8") as handle:
                self.assertIn("30", handle.read())

    def test_edit_file_safe_blocks_invalid_json(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
            file_path = os.path.join(repo_path, "config.json")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write('{"timeout": 10}\n')

            result = edit_file_safe(
                repo_path=repo_path,
                relative_path="config.json",
                content='{"timeout": }\n',
                owner="test-agent",
            )

            self.assertEqual(result.status, "failure")
            self.assertEqual(result.details["error_type"], "ValidationError")

            with open(file_path, "r", encoding="utf-8") as handle:
                self.assertIn("10", handle.read())

    def test_execute_action_routes_edit_file(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
            os.makedirs(os.path.join(repo_path, ".codecortex", "logs"), exist_ok=True)
            file_path = os.path.join(repo_path, "sample.py")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("x = 1\n")

            action = ExecutionAction(
                action="edit_file",
                repo=repo_path,
                agent_id="test-agent",
                environment="test",
                payload={"file": "sample.py", "content": "x = 2\n", "validate": True},
            )
            result = execute_action(action)

            self.assertEqual(result.status, "success")
            with open(file_path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "x = 2\n")


if __name__ == "__main__":
    unittest.main()
