import json
import os
import tempfile
import unittest
import warnings

from codecortex.execution.errors import RuntimeBypassError
from codecortex.execution.executor import execute_action
from codecortex.execution.logger import append_operation_log, normalize_log_entry
from codecortex.execution.models import ExecutionAction
from codecortex.runtime.kernel import RuntimeKernel
from codecortex.runtime.models import ActionRequest


class ExecutionLoggingTests(unittest.TestCase):
    def test_normalize_log_entry_builds_expected_shape(self):
        entry = normalize_log_entry(
            action="edit_file",
            status="success",
            repo="/repo",
            target="config.json",
            agent_id="agent-1",
            environment="openclaw",
            validation={"passed": True, "validator": "json", "errors": []},
            details={"file": "config.json"},
        )
        self.assertEqual(entry["action"], "edit_file")
        self.assertEqual(entry["status"], "success")
        self.assertEqual(entry["repo"], "/repo")
        self.assertEqual(entry["target"], "config.json")
        self.assertEqual(entry["agent_id"], "agent-1")
        self.assertEqual(entry["environment"], "openclaw")
        self.assertIn("timestamp", entry)

    def test_append_operation_log_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as repo_path:
            entry = normalize_log_entry(action="edit_file", status="success", repo=repo_path)
            log_path = append_operation_log(repo_path, entry)
            self.assertTrue(os.path.exists(log_path))
            with open(log_path, "r", encoding="utf-8") as handle:
                lines = handle.readlines()
            self.assertEqual(len(lines), 1)
            payload = json.loads(lines[0])
            self.assertEqual(payload["status"], "success")

    def test_direct_execute_action_call_is_blocked(self):
        with tempfile.TemporaryDirectory() as repo_path:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                with self.assertRaises(RuntimeBypassError):
                    execute_action(
                        ExecutionAction(
                            action="run_command",
                            repo=repo_path,
                            agent_id="logger-agent",
                            environment="test",
                            payload={"command": ["python3", "-c", "print('nope')"]},
                        )
                    )
            self.assertTrue(caught)
            self.assertIn("deprecated as a public surface", str(caught[0].message))

    def test_runtime_kernel_logs_successful_edit(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
            with open(
                os.path.join(repo_path, ".codecortex", "meta.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    {
                        "schema_version": "1.1",
                        "repo_id": "repo-123",
                        "initialized_at": "2026-03-25T00:00:00+00:00",
                    },
                    handle,
                )
            with open(
                os.path.join(repo_path, ".codecortex", "state.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    {
                        "repo_initialized": True,
                        "graph_dirty": False,
                        "last_action_at": None,
                        "last_action_id": None,
                        "last_scan_at": None,
                        "last_scan_commit": None,
                    },
                    handle,
                )
            file_path = os.path.join(repo_path, "sample.py")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("x = 1\n")

            result = RuntimeKernel().handle_action(
                ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    agent_id="logger-agent",
                    environment="test",
                    payload={"file": "sample.py", "content": "x = 3\n", "validate": True},
                )
            )
            self.assertEqual(result.status, "success")

            log_path = os.path.join(repo_path, ".codecortex", "logs", "operations.jsonl")
            self.assertTrue(os.path.exists(log_path))
            with open(log_path, "r", encoding="utf-8") as handle:
                entries = [json.loads(line) for line in handle if line.strip()]

            self.assertTrue(entries)
            last = entries[-1]
            self.assertEqual(last["action"], "edit_file")
            self.assertEqual(last["status"], "success")
            self.assertEqual(last["agent_id"], "logger-agent")
            self.assertEqual(last["environment"], "test")
            self.assertEqual(last["target"], "sample.py")
            self.assertEqual(last["details"]["stage"], "memory_feedback")


if __name__ == "__main__":
    unittest.main()
