import json
import os
import tempfile
import unittest

from codecortex.execution.logger import get_logs_dir
from codecortex.runtime.gateway import AgentGateway


class RuntimeLoopEndToEndTests(unittest.TestCase):
    def _write_runtime_meta(self, repo_path):
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

    def _write_constraints(self, repo_path, payload):
        with open(
            os.path.join(repo_path, ".codecortex", "constraints.json"),
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(payload, handle)

    def _read_state(self, repo_path):
        with open(
            os.path.join(repo_path, ".codecortex", "state.json"),
            "r",
            encoding="utf-8",
        ) as handle:
            return json.load(handle)

    def _read_operation_log(self, repo_path):
        log_path = os.path.join(get_logs_dir(repo_path), "operations.jsonl")
        with open(log_path, "r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def test_gateway_runs_full_runtime_loop_for_allowed_action(self):
        with tempfile.TemporaryDirectory() as repo_path:
            self._write_runtime_meta(repo_path)
            gateway = AgentGateway()

            response = gateway.handle_action(
                {
                    "action": "run_command",
                    "repo": repo_path,
                    "agent_id": "e2e-agent",
                    "environment": "local_cli",
                    "payload": {
                        "command": ["python3", "-c", "print('runtime-loop-ok')"],
                        "timeout_seconds": 10,
                    },
                }
            )

            self.assertEqual(response.status, "success")
            self.assertTrue(response.policy.allowed)
            self.assertTrue(response.memory.applied)
            self.assertIn("runtime-loop-ok", response.result["stdout"])

            state = self._read_state(repo_path)
            self.assertIsNotNone(state["last_action_at"])
            self.assertTrue(state["last_action_id"].startswith("run_command:"))
            self.assertFalse(state["graph_dirty"])

            entries = self._read_operation_log(repo_path)
            self.assertEqual([entry["status"] for entry in entries], ["success", "success"])
            self.assertEqual(entries[0]["action"], "run_command")
            self.assertEqual(entries[0]["target"], "<command>")
            self.assertEqual(entries[1]["details"]["stage"], "memory_feedback")
            self.assertEqual(entries[1]["details"]["execution_status"], "success")

    def test_gateway_blocks_action_before_execution(self):
        with tempfile.TemporaryDirectory() as repo_path:
            self._write_runtime_meta(repo_path)
            self._write_constraints(
                repo_path,
                {"path_write_rules": [{"mode": "deny", "pattern": "docs/**"}]},
            )
            os.makedirs(os.path.join(repo_path, "docs"), exist_ok=True)
            target_path = os.path.join(repo_path, "docs", "guide.md")
            with open(target_path, "w", encoding="utf-8") as handle:
                handle.write("original\n")

            gateway = AgentGateway()
            response = gateway.handle_action(
                {
                    "action": "edit_file",
                    "repo": repo_path,
                    "agent_id": "e2e-agent",
                    "environment": "local_cli",
                    "payload": {
                        "file": "docs/guide.md",
                        "content": "blocked\n",
                        "validate": True,
                        "lock_ttl_seconds": 30,
                    },
                }
            )

            self.assertEqual(response.status, "blocked")
            self.assertFalse(response.policy.allowed)
            self.assertFalse(response.memory.applied)
            self.assertEqual(response.error["error_type"], "PolicyViolation")

            with open(target_path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "original\n")

            state = self._read_state(repo_path)
            self.assertIsNone(state["last_action_at"])
            self.assertIsNone(state["last_action_id"])
            self.assertFalse(os.path.exists(os.path.join(get_logs_dir(repo_path), "operations.jsonl")))

    def test_gateway_marks_graph_dirty_after_python_edit(self):
        with tempfile.TemporaryDirectory() as repo_path:
            self._write_runtime_meta(repo_path)
            os.makedirs(os.path.join(repo_path, "pkg"), exist_ok=True)
            target_path = os.path.join(repo_path, "pkg", "module.py")
            with open(target_path, "w", encoding="utf-8") as handle:
                handle.write("def old_name():\n    return 1\n")

            gateway = AgentGateway()
            response = gateway.handle_action(
                {
                    "action": "edit_file",
                    "repo": repo_path,
                    "agent_id": "e2e-agent",
                    "environment": "local_cli",
                    "payload": {
                        "file": "pkg/module.py",
                        "content": "def new_name():\n    return 2\n",
                        "validate": True,
                        "lock_ttl_seconds": 30,
                    },
                }
            )

            self.assertEqual(response.status, "success")
            self.assertTrue(response.policy.allowed)
            self.assertTrue(response.memory.applied)
            self.assertTrue(response.memory.state_updates["graph_dirty"])
            self.assertEqual(response.memory.details["changed_python_files"], ["pkg/module.py"])

            with open(target_path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "def new_name():\n    return 2\n")

            state = self._read_state(repo_path)
            self.assertTrue(state["graph_dirty"])
            self.assertTrue(state["last_action_id"].startswith("edit_file:"))


if __name__ == "__main__":
    unittest.main()
