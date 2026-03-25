import json
import os
import tempfile
import unittest

from codecortex.execution.errors import RuntimeBypassError
from codecortex.execution.models import ExecutionResult
from codecortex.runtime.kernel import RuntimeKernel
from codecortex.runtime.execution_bridge import ExecutionBridge
from codecortex.runtime.models import ActionRequest, MemoryUpdateResult


class RuntimeKernelTests(unittest.TestCase):
    def test_handle_action_does_not_invoke_execution_when_policy_blocks(self):
        class BlockingPolicyEngine:
            def evaluate(self, context):
                from codecortex.runtime.models import PolicyDecision

                return PolicyDecision(
                    allowed=False,
                    reason="blocked for test",
                    violations=["blocked_for_test"],
                    details={"stage": "policy_engine"},
                )

        class SpyExecutionBridge:
            def __init__(self):
                self.called = False

            def execute(self, context):
                self.called = True
                return ExecutionResult(
                    status="success",
                    action=context.request.action if context.request else "unknown",
                    details={},
                )

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

            bridge = SpyExecutionBridge()
            response = RuntimeKernel(
                policy_engine=BlockingPolicyEngine(),
                execution_bridge=bridge,
            ).handle_action(
                ActionRequest(
                    action="run_command",
                    repo=repo_path,
                    payload={"command": ["python3", "-c", "print('blocked')"]},
                )
            )

            self.assertEqual(response.status, "blocked")
            self.assertFalse(bridge.called)

    def test_handle_action_routes_memory_feedback_component(self):
        class SpyMemoryFeedback:
            def __init__(self):
                self.context = None
                self.result = None

            def apply(self, context, result):
                self.context = context
                self.result = result
                return MemoryUpdateResult(
                    applied=True,
                    state_updates={"last_action_id": "memory:test"},
                    details={"stage": "memory_feedback"},
                )

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

            feedback = SpyMemoryFeedback()
            response = RuntimeKernel(memory_feedback=feedback).handle_action(
                ActionRequest(
                    action="run_command",
                    repo=repo_path,
                    agent_id="kernel-agent",
                    environment="test",
                    payload={"command": ["python3", "-c", "print('memory')"]},
                )
            )

            self.assertEqual(response.status, "success")
            self.assertTrue(response.memory.applied)
            self.assertEqual(response.memory.details["stage"], "memory_feedback")
            self.assertIsNotNone(feedback.context)
            self.assertEqual(feedback.result["status"], "success")

    def test_handle_action_blocks_repo_without_valid_meta(self):
        with tempfile.TemporaryDirectory() as repo_path:
            response = RuntimeKernel().handle_action(
                ActionRequest(
                    action="run_command",
                    repo=repo_path,
                    agent_id="kernel-agent",
                    environment="test",
                    payload={"command": ["python3", "-c", "print('blocked')"]},
                )
            )

            self.assertEqual(response.status, "blocked")
            self.assertFalse(response.policy.allowed)
            self.assertEqual(response.error["error_type"], "RepoNotEnabled")
            self.assertFalse(response.memory.applied)

    def test_handle_action_blocks_when_state_json_is_missing(self):
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
            file_path = os.path.join(repo_path, "sample.py")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("x = 1\n")

            response = RuntimeKernel().handle_action(
                ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    payload={"file": "sample.py", "content": "x = 2\n"},
                )
            )

            self.assertEqual(response.status, "blocked")
            self.assertFalse(response.policy.allowed)
            self.assertIn("missing or invalid", response.policy.reason)
            with open(file_path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "x = 1\n")

    def test_handle_action_routes_edit_file_and_returns_envelope(self):
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

            response = RuntimeKernel().handle_action(
                ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    agent_id="kernel-agent",
                    environment="test",
                    payload={
                        "file": "sample.py",
                        "content": "x = 2\n",
                        "validate": True,
                        "lock_ttl_seconds": 30,
                    },
                )
            )

            self.assertEqual(response.status, "success")
            self.assertEqual(response.action, "edit_file")
            self.assertTrue(response.policy.allowed)
            self.assertTrue(response.memory.applied)
            self.assertIn("stage", response.policy.details)
            self.assertIn("stage", response.memory.details)
            self.assertTrue(response.memory.state_updates["graph_dirty"])

            with open(file_path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "x = 2\n")

            with open(
                os.path.join(repo_path, ".codecortex", "state.json"),
                "r",
                encoding="utf-8",
            ) as handle:
                state = json.load(handle)
            self.assertTrue(state["graph_dirty"])
            self.assertIsNotNone(state["last_action_at"])
            self.assertTrue(state["last_action_id"].startswith("edit_file:"))
            self.assertEqual(response.memory.details["stage"], "memory_feedback")
            self.assertTrue(response.memory.details["log_path"].endswith("operations.jsonl"))

    def test_handle_action_does_not_mark_graph_dirty_for_non_python_edit(self):
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
            file_path = os.path.join(repo_path, "README.md")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("before\n")

            response = RuntimeKernel().handle_action(
                ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    agent_id="kernel-agent",
                    environment="test",
                    payload={
                        "file": "README.md",
                        "content": "after\n",
                        "validate": True,
                        "lock_ttl_seconds": 30,
                    },
                )
            )

            self.assertEqual(response.status, "success")
            self.assertNotIn("graph_dirty", response.memory.state_updates)

            with open(
                os.path.join(repo_path, ".codecortex", "state.json"),
                "r",
                encoding="utf-8",
            ) as handle:
                state = json.load(handle)
            self.assertFalse(state["graph_dirty"])

    def test_handle_action_auto_updates_graph_when_requested(self):
        with tempfile.TemporaryDirectory() as repo_path:
            state_dir = os.path.join(repo_path, ".codecortex")
            os.makedirs(os.path.join(state_dir, "locks"), exist_ok=True)
            os.makedirs(os.path.join(repo_path, "pkg"), exist_ok=True)
            with open(os.path.join(state_dir, "meta.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.1",
                        "repo_id": "repo-123",
                        "initialized_at": "2026-03-25T00:00:00+00:00",
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "state.json"), "w", encoding="utf-8") as handle:
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
            with open(os.path.join(repo_path, "pkg", "__init__.py"), "w", encoding="utf-8") as handle:
                handle.write("")
            module_path = os.path.join(repo_path, "pkg", "module.py")
            with open(module_path, "w", encoding="utf-8") as handle:
                handle.write("def old_name():\n    return 1\n")

            from codecortex.graph_builder import build_graph, save_graph

            save_graph(build_graph(repo_path, generated_at="t1", git_commit="c1"), repo_path)

            response = RuntimeKernel().handle_action(
                ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    agent_id="kernel-agent",
                    environment="test",
                    payload={
                        "file": "pkg/module.py",
                        "content": "def new_name():\n    return 2\n",
                        "validate": True,
                        "lock_ttl_seconds": 30,
                        "auto_update_graph": True,
                    },
                )
            )

            self.assertEqual(response.status, "success")
            self.assertFalse(response.memory.state_updates["graph_dirty"])
            self.assertTrue(response.memory.details["graph_update"]["applied"])

            with open(os.path.join(state_dir, "state.json"), "r", encoding="utf-8") as handle:
                state = json.load(handle)
            self.assertFalse(state["graph_dirty"])
            self.assertIsNotNone(state["last_scan_at"])

            with open(os.path.join(state_dir, "graph.json"), "r", encoding="utf-8") as handle:
                graph = json.load(handle)
            node_ids = {node["id"] for node in graph["nodes"]}
            self.assertIn("function:pkg.module.new_name", node_ids)
            self.assertNotIn("function:pkg.module.old_name", node_ids)

    def test_handle_action_marks_graph_dirty_after_mutating_command(self):
        with tempfile.TemporaryDirectory() as repo_path:
            state_dir = os.path.join(repo_path, ".codecortex")
            os.makedirs(os.path.join(state_dir, "locks"), exist_ok=True)
            with open(os.path.join(state_dir, "meta.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.1",
                        "repo_id": "repo-123",
                        "initialized_at": "2026-03-25T00:00:00+00:00",
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "state.json"), "w", encoding="utf-8") as handle:
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

            response = RuntimeKernel().handle_action(
                ActionRequest(
                    action="run_command",
                    repo=repo_path,
                    agent_id="kernel-agent",
                    environment="test",
                    payload={
                        "command": [
                            "python3",
                            "-c",
                            "from pathlib import Path; Path('generated.py').write_text('x = 1\\n', encoding='utf-8')",
                        ],
                    },
                )
            )

            self.assertEqual(response.status, "success")
            self.assertTrue(response.memory.applied)
            self.assertTrue(response.memory.state_updates["graph_dirty"])
            self.assertEqual(response.memory.details["changed_python_files"], ["generated.py"])

            with open(os.path.join(state_dir, "state.json"), "r", encoding="utf-8") as handle:
                state = json.load(handle)
            self.assertTrue(state["graph_dirty"])

    def test_handle_action_records_decision_when_requested(self):
        with tempfile.TemporaryDirectory() as repo_path:
            state_dir = os.path.join(repo_path, ".codecortex")
            os.makedirs(os.path.join(state_dir, "locks"), exist_ok=True)
            with open(os.path.join(state_dir, "meta.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.1",
                        "repo_id": "repo-123",
                        "initialized_at": "2026-03-25T00:00:00+00:00",
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "state.json"), "w", encoding="utf-8") as handle:
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

            response = RuntimeKernel().handle_action(
                ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    agent_id="kernel-agent",
                    environment="test",
                    payload={
                        "file": "sample.py",
                        "content": "x = 2\n",
                        "decision": {
                            "title": "Keep sample stable",
                            "summary": "Edit preserves current module semantics.",
                            "scope": "sample",
                        },
                    },
                )
            )

            self.assertEqual(response.status, "success")
            self.assertTrue(response.memory.details["decision_update"]["applied"])

            with open(os.path.join(state_dir, "decisions.jsonl"), "r", encoding="utf-8") as handle:
                entries = [json.loads(line) for line in handle if line.strip()]
            self.assertEqual(entries[-1]["title"], "Keep sample stable")
            self.assertEqual(entries[-1]["references"], ["sample.py"])

    def test_execution_bridge_blocks_direct_bypass(self):
        with tempfile.TemporaryDirectory() as repo_path:
            with self.assertRaises(RuntimeBypassError):
                ExecutionBridge().execute(
                    type(
                        "Context",
                        (),
                        {
                            "repo": repo_path,
                            "request": ActionRequest(
                                action="run_command",
                                repo=repo_path,
                                payload={"command": ["python3", "-c", "print('nope')"]},
                            ),
                        },
                    )()
                )

    def test_handle_action_binds_nested_path_to_repo_root(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
            os.makedirs(os.path.join(repo_path, "pkg", "nested"), exist_ok=True)
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

            response = RuntimeKernel().handle_action(
                ActionRequest(
                    action="edit_file",
                    repo=os.path.join(repo_path, "pkg", "nested"),
                    agent_id="kernel-agent",
                    environment="test",
                    payload={"file": "sample.py", "content": "x = 3\n"},
                )
            )

            self.assertEqual(response.status, "success")
            self.assertEqual(response.memory.details["repo"], repo_path)

    def test_handle_action_builds_context_with_merged_memory(self):
        with tempfile.TemporaryDirectory() as repo_path:
            state_dir = os.path.join(repo_path, ".codecortex")
            os.makedirs(os.path.join(state_dir, "locks"), exist_ok=True)
            with open(os.path.join(state_dir, "meta.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.1",
                        "repo_id": "repo-123",
                        "initialized_at": "2026-03-25T00:00:00+00:00",
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "state.json"), "w", encoding="utf-8") as handle:
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
            with open(os.path.join(state_dir, "graph.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.0",
                        "nodes": [{"id": "file:sample.py", "type": "file", "path": "sample.py"}],
                        "edges": [],
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "semantics.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.0",
                        "assertions": [
                            {
                                "id": "assert-1",
                                "subject": "file:sample.py",
                                "predicate": "implements",
                                "object": "semantic:test_rule",
                            }
                        ],
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "decisions.jsonl"), "w", encoding="utf-8") as handle:
                handle.write(json.dumps({"id": "decision-1"}) + "\n")

            file_path = os.path.join(repo_path, "sample.py")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("x = 1\n")

            captured = {}

            class InspectingKernel(RuntimeKernel):
                def _evaluate_policy(self, context):
                    captured["context"] = context
                    return super()._evaluate_policy(context)

            response = InspectingKernel().handle_action(
                ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    agent_id="kernel-agent",
                    environment="test",
                    payload={"file": "sample.py", "content": "x = 4\n"},
                )
            )

            self.assertEqual(response.status, "success")
            context = captured["context"]
            self.assertEqual([decision["id"] for decision in context.decisions], ["decision-1"])
            self.assertEqual(context.semantics["assertions"][0]["id"], "assert-1")

    def test_handle_action_routes_execution_through_bridge(self):
        class SpyExecutionBridge:
            def __init__(self):
                self.context = None

            def execute(self, context):
                self.context = context
                return ExecutionResult(
                    status="success",
                    action=context.request.action if context.request else "unknown",
                    details={"bridge": "used"},
                )

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

            bridge = SpyExecutionBridge()
            response = RuntimeKernel(execution_bridge=bridge).handle_action(
                ActionRequest(
                    action="run_command",
                    repo=repo_path,
                    agent_id="kernel-agent",
                    environment="test",
                    payload={"command": ["python3", "-c", "print('bridge')"]},
                )
            )

            self.assertEqual(response.status, "success")
            self.assertEqual(response.result["bridge"], "used")
            self.assertIsNotNone(bridge.context)
            self.assertEqual(bridge.context.repo, repo_path)
            self.assertEqual(bridge.context.request.action, "run_command")

    def test_handle_action_builds_run_command_action_context(self):
        with tempfile.TemporaryDirectory() as repo_path:
            state_dir = os.path.join(repo_path, ".codecortex")
            os.makedirs(state_dir, exist_ok=True)
            with open(os.path.join(state_dir, "meta.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.1",
                        "repo_id": "repo-123",
                        "initialized_at": "2026-03-25T00:00:00+00:00",
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "state.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "repo_initialized": True,
                        "graph_dirty": False,
                        "last_action_at": None,
                        "last_action_id": None,
                        "last_scan_at": "2026-03-25T00:00:00+00:00",
                        "last_scan_commit": "abc123",
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "graph.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.0",
                        "git_commit": "abc123",
                        "nodes": [{"id": "file:pkg/main.py", "type": "file", "path": "pkg/main.py"}],
                        "edges": [],
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "constraints.json"), "w", encoding="utf-8") as handle:
                json.dump({"require_fresh_graph": True}, handle)

            captured = {}

            class InspectingKernel(RuntimeKernel):
                def _evaluate_policy(self, context):
                    captured["context"] = context
                    return super()._evaluate_policy(context)

            response = InspectingKernel().handle_action(
                ActionRequest(
                    action="run_command",
                    repo=repo_path,
                    agent_id="kernel-agent",
                    environment="test",
                    payload={"command": ["python3", "-c", "print('ctx')"], "timeout_seconds": 10},
                )
            )

            self.assertEqual(response.status, "success")
            context = captured["context"]
            self.assertEqual(context.action_context["kind"], "run_command")
            self.assertEqual(context.action_context["graph_freshness"]["graph_status"], "fresh")
            self.assertEqual(context.action_context["command_policy_input"]["program"], "python3")
            self.assertEqual(
                context.action_context["relevant_command_policy_rules"],
                [{"type": "require_fresh_graph", "value": True}],
            )

    def test_handle_action_blocks_edit_file_before_execution_when_path_rule_matches(self):
        with tempfile.TemporaryDirectory() as repo_path:
            state_dir = os.path.join(repo_path, ".codecortex")
            os.makedirs(os.path.join(state_dir, "locks"), exist_ok=True)
            with open(os.path.join(state_dir, "meta.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.1",
                        "repo_id": "repo-123",
                        "initialized_at": "2026-03-25T00:00:00+00:00",
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "state.json"), "w", encoding="utf-8") as handle:
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
            with open(os.path.join(state_dir, "constraints.json"), "w", encoding="utf-8") as handle:
                json.dump({"path_write_rules": [{"mode": "deny", "pattern": "docs/**"}]}, handle)

            os.makedirs(os.path.join(repo_path, "docs"), exist_ok=True)
            file_path = os.path.join(repo_path, "docs", "guide.md")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("original\n")

            response = RuntimeKernel().handle_action(
                ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    agent_id="kernel-agent",
                    environment="test",
                    payload={"file": "docs/guide.md", "content": "blocked\n"},
                )
            )

            self.assertEqual(response.status, "blocked")
            self.assertFalse(response.policy.allowed)
            self.assertEqual(response.error["error_type"], "PolicyViolation")
            self.assertFalse(response.memory.applied)
            with open(file_path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "original\n")

    def test_handle_action_blocks_edit_file_with_absolute_repo_path_when_path_rule_matches(self):
        with tempfile.TemporaryDirectory() as repo_path:
            state_dir = os.path.join(repo_path, ".codecortex")
            os.makedirs(os.path.join(state_dir, "locks"), exist_ok=True)
            with open(os.path.join(state_dir, "meta.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.1",
                        "repo_id": "repo-123",
                        "initialized_at": "2026-03-25T00:00:00+00:00",
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "state.json"), "w", encoding="utf-8") as handle:
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
            with open(os.path.join(state_dir, "constraints.json"), "w", encoding="utf-8") as handle:
                json.dump({"path_write_rules": [{"mode": "deny", "pattern": "docs/**"}]}, handle)

            os.makedirs(os.path.join(repo_path, "docs"), exist_ok=True)
            file_path = os.path.join(repo_path, "docs", "guide.md")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("original\n")

            response = RuntimeKernel().handle_action(
                ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    payload={"file": file_path, "content": "blocked\n"},
                )
            )

            self.assertEqual(response.status, "blocked")
            self.assertFalse(response.policy.allowed)
            with open(file_path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "original\n")

    def test_handle_action_blocks_run_command_before_execution_when_program_denied(self):
        with tempfile.TemporaryDirectory() as repo_path:
            state_dir = os.path.join(repo_path, ".codecortex")
            os.makedirs(state_dir, exist_ok=True)
            with open(os.path.join(state_dir, "meta.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.1",
                        "repo_id": "repo-123",
                        "initialized_at": "2026-03-25T00:00:00+00:00",
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "state.json"), "w", encoding="utf-8") as handle:
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
            with open(os.path.join(state_dir, "constraints.json"), "w", encoding="utf-8") as handle:
                json.dump({"command_rules": [{"type": "deny_program", "program": "python3"}]}, handle)

            response = RuntimeKernel().handle_action(
                ActionRequest(
                    action="run_command",
                    repo=repo_path,
                    agent_id="kernel-agent",
                    environment="test",
                    payload={"command": ["python3", "-c", "print('should-not-run')"], "timeout_seconds": 10},
                )
            )

            self.assertEqual(response.status, "blocked")
            self.assertFalse(response.policy.allowed)
            self.assertEqual(response.error["error_type"], "PolicyViolation")
            self.assertFalse(response.memory.applied)

    def test_handle_action_blocks_run_command_when_effective_program_inside_shell_wrapper_is_denied(self):
        with tempfile.TemporaryDirectory() as repo_path:
            state_dir = os.path.join(repo_path, ".codecortex")
            os.makedirs(state_dir, exist_ok=True)
            with open(os.path.join(state_dir, "meta.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.1",
                        "repo_id": "repo-123",
                        "initialized_at": "2026-03-25T00:00:00+00:00",
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "state.json"), "w", encoding="utf-8") as handle:
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
            with open(os.path.join(state_dir, "constraints.json"), "w", encoding="utf-8") as handle:
                json.dump({"command_rules": [{"type": "deny_program", "program": "python3"}]}, handle)

            response = RuntimeKernel().handle_action(
                ActionRequest(
                    action="run_command",
                    repo=repo_path,
                    payload={"command": ["bash", "-lc", 'python3 -c "print(123)"'], "timeout_seconds": 10},
                )
            )

            self.assertEqual(response.status, "blocked")
            self.assertFalse(response.policy.allowed)
            self.assertIn("python3", response.policy.reason)

    def test_handle_action_blocks_mutating_action_from_openclaw_without_agent_id(self):
        with tempfile.TemporaryDirectory() as repo_path:
            state_dir = os.path.join(repo_path, ".codecortex")
            os.makedirs(os.path.join(state_dir, "locks"), exist_ok=True)
            with open(os.path.join(state_dir, "meta.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.1",
                        "repo_id": "repo-123",
                        "initialized_at": "2026-03-25T00:00:00+00:00",
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "state.json"), "w", encoding="utf-8") as handle:
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
                handle.write("value = 1\n")

            response = RuntimeKernel().handle_action(
                ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    environment="openclaw",
                    payload={"file": "sample.py", "content": "value = 2\n"},
                )
            )

            self.assertEqual(response.status, "blocked")
            self.assertFalse(response.policy.allowed)
            self.assertEqual(response.error["error_type"], "PolicyViolation")
            self.assertIn("requires agent_id", response.policy.reason)
            with open(file_path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "value = 1\n")

    def test_handle_action_allows_edit_file_with_repo_state_warning_when_graph_missing(self):
        with tempfile.TemporaryDirectory() as repo_path:
            state_dir = os.path.join(repo_path, ".codecortex")
            os.makedirs(os.path.join(state_dir, "locks"), exist_ok=True)
            with open(os.path.join(state_dir, "meta.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.1",
                        "repo_id": "repo-123",
                        "initialized_at": "2026-03-25T00:00:00+00:00",
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "state.json"), "w", encoding="utf-8") as handle:
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

            response = RuntimeKernel().handle_action(
                ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    agent_id="kernel-agent",
                    environment="test",
                    payload={"file": "sample.py", "content": "x = 7\n"},
                )
            )

            self.assertEqual(response.status, "success")
            self.assertTrue(response.policy.allowed)
            self.assertIn("warnings", response.policy.details)
            self.assertIn("degraded", response.policy.details["warnings"][0])

    def test_handle_action_blocks_edit_file_when_fresh_graph_required_and_graph_dirty(self):
        with tempfile.TemporaryDirectory() as repo_path:
            state_dir = os.path.join(repo_path, ".codecortex")
            os.makedirs(os.path.join(state_dir, "locks"), exist_ok=True)
            with open(os.path.join(state_dir, "meta.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.1",
                        "repo_id": "repo-123",
                        "initialized_at": "2026-03-25T00:00:00+00:00",
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "state.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "repo_initialized": True,
                        "graph_dirty": True,
                        "last_action_at": None,
                        "last_action_id": None,
                        "last_scan_at": "2026-03-25T00:00:00+00:00",
                        "last_scan_commit": "abc123",
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "graph.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.0",
                        "git_commit": "abc123",
                        "nodes": [{"id": "file:sample.py", "type": "file", "path": "sample.py"}],
                        "edges": [],
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "constraints.json"), "w", encoding="utf-8") as handle:
                json.dump({"require_fresh_graph": True}, handle)

            file_path = os.path.join(repo_path, "sample.py")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("x = 1\n")

            response = RuntimeKernel().handle_action(
                ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    agent_id="kernel-agent",
                    environment="test",
                    payload={"file": "sample.py", "content": "x = 8\n"},
                )
            )

            self.assertEqual(response.status, "blocked")
            self.assertFalse(response.policy.allowed)
            self.assertIn("fresh graph", response.policy.reason)
            with open(file_path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "x = 1\n")


if __name__ == "__main__":
    unittest.main()
