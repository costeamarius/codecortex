import json
import os
import tempfile
import unittest

from codecortex.graph_builder import build_graph, save_graph
from codecortex.runtime.memory_feedback import MemoryFeedback
from codecortex.runtime.models import ActionRequest, RuntimeContext


class MemoryFeedbackTests(unittest.TestCase):
    def _write_state(self, repo_path):
        os.makedirs(os.path.join(repo_path, ".codecortex"), exist_ok=True)
        with open(os.path.join(repo_path, ".codecortex", "state.json"), "w", encoding="utf-8") as handle:
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

    def test_apply_updates_state_and_appends_memory_feedback_log(self):
        with tempfile.TemporaryDirectory() as repo_path:
            self._write_state(repo_path)
            context = RuntimeContext(
                repo=repo_path,
                state_dir=os.path.join(repo_path, ".codecortex"),
                request=ActionRequest(
                    action="run_command",
                    repo=repo_path,
                    agent_id="memory-agent",
                    environment="test",
                    payload={"command": ["python3", "-c", "print('ok')"]},
                ),
                state={
                    "repo_initialized": True,
                    "graph_dirty": False,
                    "last_action_at": None,
                    "last_action_id": None,
                    "last_scan_at": None,
                    "last_scan_commit": None,
                },
            )

            result = MemoryFeedback().apply(
                context,
                {"status": "success", "action": "run_command", "details": {"stdout": "ok\n"}},
            )

            self.assertTrue(result.applied)
            self.assertEqual(result.details["stage"], "memory_feedback")
            with open(os.path.join(repo_path, ".codecortex", "state.json"), "r", encoding="utf-8") as handle:
                state = json.load(handle)
            self.assertIsNotNone(state["last_action_at"])
            self.assertTrue(state["last_action_id"].startswith("run_command:"))

            with open(result.details["log_path"], "r", encoding="utf-8") as handle:
                entries = [json.loads(line) for line in handle if line.strip()]
            self.assertEqual(entries[-1]["details"]["stage"], "memory_feedback")
            self.assertEqual(entries[-1]["details"]["execution_status"], "success")
            self.assertEqual(entries[-1]["target"], "python3")

    def test_apply_marks_graph_dirty_only_for_successful_python_edit(self):
        with tempfile.TemporaryDirectory() as repo_path:
            self._write_state(repo_path)
            context = RuntimeContext(
                repo=repo_path,
                state_dir=os.path.join(repo_path, ".codecortex"),
                request=ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    payload={"file": "pkg/module.py", "content": "x = 2\n"},
                ),
                state={
                    "repo_initialized": True,
                    "graph_dirty": False,
                    "last_action_at": None,
                    "last_action_id": None,
                    "last_scan_at": None,
                    "last_scan_commit": None,
                },
            )

            result = MemoryFeedback().apply(
                context,
                {"status": "success", "action": "edit_file", "details": {"target_file": "pkg/module.py"}},
            )

            self.assertTrue(result.state_updates["graph_dirty"])
            with open(os.path.join(repo_path, ".codecortex", "state.json"), "r", encoding="utf-8") as handle:
                state = json.load(handle)
            self.assertTrue(state["graph_dirty"])

    def test_apply_does_not_mark_graph_dirty_for_failed_edit(self):
        with tempfile.TemporaryDirectory() as repo_path:
            self._write_state(repo_path)
            context = RuntimeContext(
                repo=repo_path,
                state_dir=os.path.join(repo_path, ".codecortex"),
                request=ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    payload={"file": "pkg/module.py", "content": "x = \n"},
                ),
                state={
                    "repo_initialized": True,
                    "graph_dirty": False,
                    "last_action_at": None,
                    "last_action_id": None,
                    "last_scan_at": None,
                    "last_scan_commit": None,
                },
            )

            result = MemoryFeedback().apply(
                context,
                {"status": "failure", "action": "edit_file", "details": {"error_type": "ValidationError"}},
            )

            self.assertNotIn("graph_dirty", result.state_updates)
            with open(os.path.join(repo_path, ".codecortex", "state.json"), "r", encoding="utf-8") as handle:
                state = json.load(handle)
            self.assertFalse(state["graph_dirty"])

    def test_apply_auto_updates_graph_and_clears_dirty_flag(self):
        with tempfile.TemporaryDirectory() as repo_path:
            self._write_state(repo_path)
            os.makedirs(os.path.join(repo_path, "pkg"), exist_ok=True)
            with open(os.path.join(repo_path, "pkg", "__init__.py"), "w", encoding="utf-8") as handle:
                handle.write("")
            module_path = os.path.join(repo_path, "pkg", "module.py")
            with open(module_path, "w", encoding="utf-8") as handle:
                handle.write("def old_name():\n    return 1\n")

            save_graph(build_graph(repo_path, generated_at="t1", git_commit="c1"), repo_path)

            with open(module_path, "w", encoding="utf-8") as handle:
                handle.write("def new_name():\n    return 2\n")

            context = RuntimeContext(
                repo=repo_path,
                state_dir=os.path.join(repo_path, ".codecortex"),
                request=ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    payload={
                        "file": "pkg/module.py",
                        "content": "def new_name():\n    return 2\n",
                        "auto_update_graph": True,
                    },
                ),
                state={
                    "repo_initialized": True,
                    "graph_dirty": False,
                    "last_action_at": None,
                    "last_action_id": None,
                    "last_scan_at": None,
                    "last_scan_commit": None,
                },
            )

            result = MemoryFeedback().apply(
                context,
                {"status": "success", "action": "edit_file", "details": {"target_file": "pkg/module.py"}},
            )

            self.assertFalse(result.state_updates["graph_dirty"])
            self.assertTrue(result.details["graph_update"]["applied"])
            self.assertEqual(result.details["graph_update"]["mode"], "auto_update_graph")
            self.assertIsNotNone(result.state_updates["last_scan_at"])

            with open(os.path.join(repo_path, ".codecortex", "state.json"), "r", encoding="utf-8") as handle:
                state = json.load(handle)
            self.assertFalse(state["graph_dirty"])
            self.assertEqual(state["last_scan_at"], result.state_updates["last_scan_at"])

            with open(os.path.join(repo_path, ".codecortex", "graph.json"), "r", encoding="utf-8") as handle:
                graph = json.load(handle)
            node_ids = {node["id"] for node in graph["nodes"]}
            self.assertIn("function:pkg.module.new_name", node_ids)
            self.assertNotIn("function:pkg.module.old_name", node_ids)
            self.assertEqual(graph["generated_at"], result.state_updates["last_scan_at"])

    def test_apply_auto_update_falls_back_to_dirty_when_graph_missing(self):
        with tempfile.TemporaryDirectory() as repo_path:
            self._write_state(repo_path)
            context = RuntimeContext(
                repo=repo_path,
                state_dir=os.path.join(repo_path, ".codecortex"),
                request=ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    payload={
                        "file": "pkg/module.py",
                        "content": "x = 2\n",
                        "auto_update_graph": True,
                    },
                ),
                state={
                    "repo_initialized": True,
                    "graph_dirty": False,
                    "last_action_at": None,
                    "last_action_id": None,
                    "last_scan_at": None,
                    "last_scan_commit": None,
                },
            )

            result = MemoryFeedback().apply(
                context,
                {"status": "success", "action": "edit_file", "details": {"target_file": "pkg/module.py"}},
            )

            self.assertTrue(result.state_updates["graph_dirty"])
            self.assertTrue(result.details["graph_update"]["attempted"])
            self.assertFalse(result.details["graph_update"]["applied"])
            self.assertEqual(result.details["graph_update"]["reason"], "graph_missing_or_invalid")

    def test_apply_records_decision_when_requested(self):
        with tempfile.TemporaryDirectory() as repo_path:
            self._write_state(repo_path)
            context = RuntimeContext(
                repo=repo_path,
                state_dir=os.path.join(repo_path, ".codecortex"),
                request=ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    agent_id="memory-agent",
                    payload={
                        "file": "pkg/module.py",
                        "content": "x = 2\n",
                        "decision": {
                            "title": "Keep module stable",
                            "summary": "This edit preserves the public module contract.",
                            "scope": "pkg.module",
                        },
                    },
                ),
                state={
                    "repo_initialized": True,
                    "graph_dirty": False,
                    "last_action_at": None,
                    "last_action_id": None,
                    "last_scan_at": None,
                    "last_scan_commit": None,
                },
            )

            result = MemoryFeedback().apply(
                context,
                {"status": "success", "action": "edit_file", "details": {"target_file": "pkg/module.py"}},
            )

            self.assertTrue(result.details["decision_update"]["requested"])
            self.assertTrue(result.details["decision_update"]["applied"])
            decisions_path = os.path.join(repo_path, ".codecortex", "decisions.jsonl")
            with open(decisions_path, "r", encoding="utf-8") as handle:
                entries = [json.loads(line) for line in handle if line.strip()]
            self.assertEqual(entries[-1]["title"], "Keep module stable")
            self.assertEqual(entries[-1]["references"], ["pkg/module.py"])
            self.assertEqual(entries[-1]["agent_id"], "memory-agent")
