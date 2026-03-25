import json
import os
import tempfile
import unittest

from codecortex.runtime.capabilities import build_capabilities_snapshot


class RuntimeCapabilitiesTests(unittest.TestCase):
    def test_reports_uninitialized_repo(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex"), exist_ok=True)

            payload = build_capabilities_snapshot(repo_path)

            self.assertFalse(payload["codecortex_enabled"])
            self.assertFalse(payload["runtime"]["repo_initialized"])
            self.assertFalse(payload["runtime"]["readiness"]["runtime_actions_available"])
            self.assertEqual(payload["runtime"]["graph_status"], "missing")
            self.assertEqual(payload["runtime"]["ingress"]["cli_command"], "cortex action")
            self.assertIn("not CodeCortex-enabled", payload["runtime"]["warnings"][0])
            self.assertEqual(payload["runtime"]["constraint_issues"], [])
            self.assertEqual(payload["runtime"]["constraints_active"]["path_write_rules"], 1)

    def test_reports_initialized_repo_without_graph(self):
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
                json.dump({"require_fresh_graph": False}, handle)

            payload = build_capabilities_snapshot(repo_path)

            self.assertTrue(payload["codecortex_enabled"])
            self.assertTrue(payload["runtime"]["repo_initialized"])
            self.assertFalse(payload["runtime"]["graph_present"])
            self.assertEqual(payload["runtime"]["graph_status"], "missing")
            self.assertTrue(payload["runtime"]["constraints_loaded"])
            self.assertIn("graph is missing", " ".join(payload["runtime"]["warnings"]))
            self.assertEqual(payload["runtime"]["constraint_issues"], [])

    def test_reports_initialized_repo_with_fresh_graph(self):
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
                json.dump(
                    {
                        "require_fresh_graph": True,
                        "path_write_rules": [{"mode": "deny", "pattern": "docs/**"}],
                        "command_rules": [{"type": "deny_program", "program": "rm"}],
                    },
                    handle,
                )

            payload = build_capabilities_snapshot(repo_path)

            self.assertTrue(payload["runtime"]["repo_initialized"])
            self.assertTrue(payload["runtime"]["graph_present"])
            self.assertEqual(payload["runtime"]["graph_status"], "fresh")
            self.assertTrue(payload["runtime"]["readiness"]["graph_context_fresh"])
            self.assertEqual(payload["runtime"]["constraints_active"]["path_write_rules"], 1)
            self.assertEqual(payload["runtime"]["constraints_active"]["command_rules"], 1)
            self.assertTrue(payload["runtime"]["constraints_active"]["require_fresh_graph"])
            self.assertEqual(payload["runtime"]["supported_actions"], ["edit_file", "run_command"])
            self.assertTrue(payload["runtime"]["ingress"]["structured_json_required"])
            self.assertEqual(
                payload["execution"]["deprecated_public_surfaces"]["cli_commands"],
                ["edit-file", "run-command"],
            )
            self.assertEqual(payload["runtime"]["warnings"], [])
            self.assertEqual(payload["runtime"]["constraint_issues"], [])

    def test_reports_invalid_constraints_and_uses_default_policy_fallback(self):
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
                json.dump({"path_write_rules": "bad"}, handle)

            payload = build_capabilities_snapshot(repo_path)

            self.assertTrue(payload["runtime"]["constraint_issues"])
            self.assertEqual(payload["runtime"]["constraints_active"]["path_write_rules"], 0)


if __name__ == "__main__":
    unittest.main()
