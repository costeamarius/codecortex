import json
import os
import tempfile
import unittest

from codecortex.runtime.context_builder import ContextBuilder
from codecortex.runtime.models import ActionRequest


class ContextBuilderTests(unittest.TestCase):
    def test_build_loads_merged_repo_memory(self):
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
            with open(os.path.join(state_dir, "graph.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.0",
                        "nodes": [
                            {"id": "file:pkg/module.py", "type": "file", "path": "pkg/module.py"},
                            {
                                "id": "module:pkg.other",
                                "type": "module",
                                "name": "pkg.other",
                                "scope": "internal",
                            },
                            {
                                "id": "module:pkg.module",
                                "type": "module",
                                "name": "pkg.module",
                                "scope": "internal",
                            },
                            {
                                "id": "function:pkg.module.run",
                                "type": "function",
                                "name": "run",
                                "qualname": "pkg.module.run",
                                "path": "pkg/module.py",
                                "module": "pkg.module",
                                "line": 3,
                            },
                            {
                                "id": "function:pkg.other.use_run",
                                "type": "function",
                                "name": "use_run",
                                "qualname": "pkg.other.use_run",
                                "path": "pkg/other.py",
                                "module": "pkg.other",
                                "line": 2,
                            },
                        ],
                        "edges": [
                            {"from": "file:pkg/module.py", "to": "module:pkg.other", "type": "imports"},
                            {"from": "file:pkg/module.py", "to": "function:pkg.module.run", "type": "defines"},
                            {"from": "file:pkg/consumer.py", "to": "module:pkg.module", "type": "imports"},
                            {
                                "from": "function:pkg.other.use_run",
                                "to": "function:pkg.module.run",
                                "type": "calls",
                                "line": 7,
                            },
                        ],
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
                                "subject": "file:pkg/module.py",
                                "predicate": "implements",
                                "object": "semantic:repo_rule",
                                "confidence": "high",
                            },
                            {
                                "id": "assert-2",
                                "subject": "function:pkg.module.run",
                                "predicate": "used_by",
                                "object": "function:pkg.other.use_run",
                            },
                            {
                                "id": "assert-3",
                                "subject": "file:pkg/elsewhere.py",
                                "predicate": "implements",
                                "object": "semantic:unrelated",
                            },
                        ],
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "constraints.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "path_write_rule": {"mode": "deny", "pattern": "docs/**"},
                        "constraints": ["stay in repo"],
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "decisions.jsonl"), "w", encoding="utf-8") as handle:
                handle.write(json.dumps({"id": "decision-1", "scope": "pkg.module"}) + "\n")
                handle.write(json.dumps({"id": "decision-1b", "path": "pkg/module.py"}) + "\n")
                handle.write("{invalid-json}\n")
                handle.write(json.dumps({"id": "decision-2", "scope": "repo"}) + "\n")

            context = ContextBuilder().build(
                repo_path,
                ActionRequest(
                    action="edit_file",
                    repo=os.path.join(repo_path, "nested"),
                    payload={"file": "pkg/module.py", "content": "x = 2\n"},
                    agent_id="agent-1",
                    environment="test",
                ),
            )

            self.assertEqual(context.repo, repo_path)
            self.assertEqual(context.request.repo, repo_path)
            self.assertEqual(context.meta["repo_id"], "repo-123")
            self.assertFalse(context.state["graph_dirty"])
            self.assertEqual(context.constraints["constraints"], ["stay in repo"])
            self.assertEqual(
                context.constraints["path_write_rules"],
                [{"mode": "deny", "pattern": "docs/**"}],
            )
            self.assertEqual(
                [decision["id"] for decision in context.decisions],
                ["decision-1", "decision-1b", "decision-2"],
            )
            self.assertEqual(context.semantics["assertions"][0]["id"], "assert-1")
            self.assertEqual(len(context.graph["nodes"]), 8)
            assertion_ids = {
                edge["assertion_id"]
                for edge in context.graph["edges"]
                if edge.get("assertion_id")
            }
            self.assertEqual(assertion_ids, {"assert-1", "assert-2", "assert-3"})
            self.assertEqual(context.action_context["kind"], "edit_file")
            self.assertTrue(context.action_context["repo_state"]["repo_initialized"])
            self.assertFalse(context.action_context["repo_state"]["graph_dirty"])
            self.assertEqual(context.action_context["graph_freshness"]["graph_status"], "fresh")
            self.assertTrue(context.action_context["file_found"])
            self.assertEqual(context.action_context["file_node"]["id"], "file:pkg/module.py")
            self.assertEqual(context.action_context["imported_by"], ["file:pkg/consumer.py"])
            self.assertEqual(
                [node["id"] for node in context.action_context["symbols_defined"]],
                ["function:pkg.module.run"],
            )
            self.assertEqual(
                [edge["type"] for edge in context.action_context["symbol_relations"]],
                ["defines", "calls", "used_by"],
            )
            self.assertEqual(
                [assertion["id"] for assertion in context.action_context["relevant_semantic_assertions"]],
                ["assert-1", "assert-2"],
            )
            self.assertEqual(
                [decision["id"] for decision in context.action_context["recent_decisions"]],
                ["decision-1", "decision-1b"],
            )

    def test_build_uses_decision_store_query_for_recent_decisions(self):
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
            with open(os.path.join(state_dir, "graph.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.0",
                        "nodes": [
                            {"id": "file:pkg/module.py", "type": "file", "path": "pkg/module.py"},
                            {
                                "id": "module:pkg.module",
                                "type": "module",
                                "name": "pkg.module",
                                "scope": "internal",
                            },
                        ],
                        "edges": [],
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "decisions.jsonl"), "w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "id": "decision-1",
                            "title": "Module policy",
                            "summary": "Preserve pkg.module behavior.",
                            "scope": "pkg.module",
                            "references": ["pkg/module.py"],
                        }
                    )
                    + "\n"
                )
                handle.write(
                    json.dumps(
                        {
                            "id": "decision-2",
                            "title": "Repo note",
                            "summary": "General repo note.",
                            "scope": "repo",
                        }
                    )
                    + "\n"
                )

            context = ContextBuilder().build(
                repo_path,
                ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    payload={"file": "pkg/module.py", "content": "x = 2\n"},
                ),
            )

            self.assertEqual(
                [decision["id"] for decision in context.action_context["recent_decisions"]],
                ["decision-1"],
            )

    def test_build_defaults_missing_memory_files(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex"), exist_ok=True)

            context = ContextBuilder().build(
                repo_path,
                ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    payload={"file": "pkg/missing.py", "content": "x = 1\n"},
                ),
            )

            self.assertEqual(context.meta, {})
            self.assertFalse(context.state["repo_initialized"])
            self.assertEqual(context.graph["nodes"], [])
            self.assertEqual(context.graph["edges"], [])
            self.assertEqual(context.semantics["assertions"], [])
            self.assertEqual(
                context.constraints,
                {
                    "schema_version": "1.0",
                    "require_fresh_graph": False,
                    "path_write_rules": [
                        {
                            "mode": "deny",
                            "pattern": "docs/**",
                            "reason": "Repository docs are not the default destination for CodeCortex runtime writes.",
                        }
                    ],
                    "command_rules": [],
                    "constraints": [
                        "Keep CodeCortex-generated project memory artifacts under .codecortex/ "
                        "(for notes use .codecortex/notes/) and avoid writing them into docs/ "
                        "or repository root."
                    ],
                },
            )
            self.assertEqual(context.decisions, [])
            self.assertEqual(context.action_context["kind"], "edit_file")
            self.assertFalse(context.action_context["repo_state"]["state_valid"])
            self.assertEqual(context.action_context["graph_freshness"]["graph_status"], "missing")
            self.assertFalse(context.action_context["file_found"])

    def test_build_normalizes_absolute_edit_file_path_into_repo_relative_context(self):
        with tempfile.TemporaryDirectory() as repo_path:
            state_dir = os.path.join(repo_path, ".codecortex")
            os.makedirs(state_dir, exist_ok=True)
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
                        "nodes": [{"id": "file:docs/guide.md", "type": "file", "path": "docs/guide.md"}],
                        "edges": [],
                    },
                    handle,
                )

            absolute_file = os.path.join(repo_path, "docs", "guide.md")
            context = ContextBuilder().build(
                repo_path,
                ActionRequest(
                    action="edit_file",
                    repo=repo_path,
                    payload={"file": absolute_file, "content": "changed\n"},
                ),
            )

            self.assertEqual(context.action_context["file"], "docs/guide.md")

    def test_build_run_command_context_extracts_effective_command_from_shell_wrapper(self):
        with tempfile.TemporaryDirectory() as repo_path:
            state_dir = os.path.join(repo_path, ".codecortex")
            os.makedirs(state_dir, exist_ok=True)
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

            context = ContextBuilder().build(
                repo_path,
                ActionRequest(
                    action="run_command",
                    repo=repo_path,
                    payload={"command": ["bash", "-lc", 'python3 -c "print(123)"']},
                ),
            )

            command_input = context.action_context["command_policy_input"]
            self.assertEqual(command_input["program"], "bash")
            self.assertEqual(command_input["effective_program"], "python3")
            self.assertEqual(command_input["classification"]["family"], "python")

    def test_build_leaves_non_edit_actions_without_action_context(self):
        with tempfile.TemporaryDirectory() as repo_path:
            state_dir = os.path.join(repo_path, ".codecortex")
            os.makedirs(state_dir, exist_ok=True)
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
                        "nodes": [{"id": "file:pkg/main.py", "type": "file", "path": "pkg/main.py"}],
                        "edges": [],
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "constraints.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "require_fresh_graph": True,
                        "command_rule": {"type": "deny_program", "program": "rm"},
                        "constraints": ["commands must execute in repo context"],
                    },
                    handle,
                )

            context = ContextBuilder().build(
                repo_path,
                ActionRequest(
                    action="run_command",
                    repo=repo_path,
                    agent_id="agent-1",
                    environment="test",
                    payload={"command": ["python3", "-m", "pytest", "-q"], "timeout_seconds": 30},
                ),
            )

            self.assertEqual(context.action_context["kind"], "run_command")
            self.assertTrue(context.action_context["repo_state"]["repo_initialized"])
            self.assertTrue(context.action_context["repo_state"]["graph_dirty"])
            self.assertEqual(context.action_context["graph_freshness"]["graph_status"], "dirty")
            self.assertEqual(context.action_context["command_policy_input"]["program"], "python3")
            self.assertEqual(context.action_context["command_policy_input"]["argc"], 4)
            self.assertEqual(context.action_context["command_policy_input"]["classification"]["family"], "test")
            self.assertTrue(context.action_context["command_policy_input"]["classification"]["is_python"])
            self.assertEqual(
                context.action_context["relevant_command_policy_rules"],
                [
                    {"type": "deny_program", "program": "rm"},
                    {"type": "require_fresh_graph", "value": True},
                    {"type": "legacy_constraint", "value": "commands must execute in repo context"},
                ],
            )


if __name__ == "__main__":
    unittest.main()
