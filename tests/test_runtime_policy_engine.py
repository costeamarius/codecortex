import unittest

from codecortex.runtime.models import ActionRequest, RuntimeContext
from codecortex.runtime.policy_engine import PolicyEngine


class PolicyEngineTests(unittest.TestCase):
    def test_blocks_uninitialized_repo_state(self):
        decision = PolicyEngine().evaluate(
            RuntimeContext(
                repo="/tmp/repo",
                request=ActionRequest(action="run_command", repo="/tmp/repo", payload={"command": ["pwd"]}),
                state={"repo_initialized": False, "graph_dirty": False},
                action_context={
                    "kind": "run_command",
                    "graph_freshness": {"graph_present": True, "graph_dirty": False},
                    "command_policy_input": {"program": "pwd", "classification": {"family": "generic"}},
                },
            )
        )

        self.assertFalse(decision.allowed)
        self.assertIn("not initialized", decision.reason)

    def test_blocks_edit_file_when_path_rule_matches(self):
        decision = PolicyEngine().evaluate(
            RuntimeContext(
                repo="/tmp/repo",
                request=ActionRequest(
                    action="edit_file",
                    repo="/tmp/repo",
                    payload={"file": "docs/guide.md", "content": "blocked\n"},
                ),
                state={"repo_initialized": True, "graph_dirty": False},
                constraints={"path_write_rules": [{"mode": "deny", "pattern": "docs/**"}]},
            )
        )

        self.assertFalse(decision.allowed)
        self.assertIn("path rule", decision.reason)

    def test_warns_when_edit_file_runs_without_graph_context(self):
        decision = PolicyEngine().evaluate(
            RuntimeContext(
                repo="/tmp/repo",
                request=ActionRequest(
                    action="edit_file",
                    repo="/tmp/repo",
                    payload={"file": "pkg/module.py", "content": "x = 2\n"},
                ),
                state={"repo_initialized": True, "graph_dirty": False},
                action_context={
                    "kind": "edit_file",
                    "graph_freshness": {"graph_present": False, "graph_dirty": False},
                },
            )
        )

        self.assertTrue(decision.allowed)
        self.assertIn("degraded", decision.details["warnings"][0])

    def test_blocks_run_command_when_program_is_denied(self):
        decision = PolicyEngine().evaluate(
            RuntimeContext(
                repo="/tmp/repo",
                request=ActionRequest(
                    action="run_command",
                    repo="/tmp/repo",
                    payload={"command": ["rm", "-rf", "tmp"]},
                ),
                state={"repo_initialized": True, "graph_dirty": False},
                constraints={"command_rules": [{"type": "deny_program", "program": "rm"}]},
                action_context={
                    "kind": "run_command",
                    "graph_freshness": {"graph_present": True, "graph_dirty": False},
                    "command_policy_input": {"program": "rm", "classification": {"family": "generic"}},
                },
            )
        )

        self.assertFalse(decision.allowed)
        self.assertIn("blocked by policy", decision.reason)

    def test_blocks_mutating_action_from_participating_environment_without_agent_id(self):
        decision = PolicyEngine().evaluate(
            RuntimeContext(
                repo="/tmp/repo",
                request=ActionRequest(
                    action="edit_file",
                    repo="/tmp/repo",
                    environment="openclaw",
                    payload={"file": "pkg/module.py", "content": "x = 2\n"},
                ),
                state={"repo_initialized": True, "graph_dirty": False},
                action_context={
                    "kind": "edit_file",
                    "repo_state": {"state_valid": True},
                    "graph_freshness": {"graph_present": True, "graph_dirty": False},
                },
            )
        )

        self.assertFalse(decision.allowed)
        self.assertIn("requires agent_id", decision.reason)
        self.assertIn(
            "agent_identity",
            [rule["family"] for rule in decision.details["matched_rules"]],
        )

    def test_allows_mutating_action_from_participating_environment_with_agent_id(self):
        decision = PolicyEngine().evaluate(
            RuntimeContext(
                repo="/tmp/repo",
                request=ActionRequest(
                    action="run_command",
                    repo="/tmp/repo",
                    agent_id="openclaw-agent",
                    environment="openclaw",
                    payload={"command": ["python3", "-m", "pytest"]},
                ),
                state={"repo_initialized": True, "graph_dirty": False},
                action_context={
                    "kind": "run_command",
                    "repo_state": {"state_valid": True},
                    "graph_freshness": {"graph_present": True, "graph_dirty": False},
                    "command_policy_input": {"program": "python3", "classification": {"family": "test"}},
                },
            )
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.details["warnings"], [])

    def test_blocks_graph_dependent_action_when_fresh_graph_required_and_missing(self):
        decision = PolicyEngine().evaluate(
            RuntimeContext(
                repo="/tmp/repo",
                request=ActionRequest(
                    action="edit_file",
                    repo="/tmp/repo",
                    payload={"file": "pkg/module.py", "content": "x = 2\n"},
                ),
                state={"repo_initialized": True, "graph_dirty": False},
                constraints={"require_fresh_graph": True},
                action_context={
                    "kind": "edit_file",
                    "graph_freshness": {"graph_present": False, "graph_dirty": False},
                },
            )
        )

        self.assertFalse(decision.allowed)
        self.assertIn("requires a graph", decision.reason)

    def test_blocks_graph_dependent_action_when_fresh_graph_required_and_dirty(self):
        decision = PolicyEngine().evaluate(
            RuntimeContext(
                repo="/tmp/repo",
                request=ActionRequest(
                    action="run_command",
                    repo="/tmp/repo",
                    payload={"command": ["python3", "-m", "pytest"]},
                ),
                state={"repo_initialized": True, "graph_dirty": True},
                constraints={"require_fresh_graph": True},
                action_context={
                    "kind": "run_command",
                    "graph_freshness": {"graph_present": True, "graph_dirty": True},
                    "command_policy_input": {"program": "python3", "classification": {"family": "test"}},
                },
            )
        )

        self.assertFalse(decision.allowed)
        self.assertIn("fresh graph", decision.reason)

    def test_allows_request_when_no_rule_blocks_it(self):
        decision = PolicyEngine().evaluate(
            RuntimeContext(
                repo="/tmp/repo",
                request=ActionRequest(
                    action="run_command",
                    repo="/tmp/repo",
                    payload={"command": ["python3", "-m", "pytest"]},
                ),
                state={"repo_initialized": True, "graph_dirty": False},
                action_context={
                    "kind": "run_command",
                    "graph_freshness": {"graph_present": True, "graph_dirty": False},
                    "command_policy_input": {"program": "python3", "classification": {"family": "test"}},
                },
            )
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.details["warnings"], [])

    def test_blocks_when_runtime_state_is_missing_or_invalid(self):
        decision = PolicyEngine().evaluate(
            RuntimeContext(
                repo="/tmp/repo",
                request=ActionRequest(
                    action="edit_file",
                    repo="/tmp/repo",
                    payload={"file": "sample.py", "content": "x = 2\n"},
                ),
                state={"repo_initialized": False, "graph_dirty": False},
                action_context={
                    "kind": "edit_file",
                    "repo_state": {"state_valid": False},
                    "graph_freshness": {"graph_present": False, "graph_dirty": False},
                },
            )
        )

        self.assertFalse(decision.allowed)
        self.assertIn("missing or invalid", decision.reason)

    def test_blocks_edit_file_when_absolute_path_matches_deny_rule_inside_repo(self):
        decision = PolicyEngine().evaluate(
            RuntimeContext(
                repo="/tmp/repo",
                request=ActionRequest(
                    action="edit_file",
                    repo="/tmp/repo",
                    payload={"file": "/tmp/repo/docs/guide.md", "content": "blocked\n"},
                ),
                state={"repo_initialized": True, "graph_dirty": False},
                action_context={"kind": "edit_file", "repo_state": {"state_valid": True}},
                constraints={"path_write_rules": [{"mode": "deny", "pattern": "docs/**"}]},
            )
        )

        self.assertFalse(decision.allowed)
        self.assertIn("path rule", decision.reason)

    def test_blocks_run_command_when_effective_program_is_denied(self):
        decision = PolicyEngine().evaluate(
            RuntimeContext(
                repo="/tmp/repo",
                request=ActionRequest(
                    action="run_command",
                    repo="/tmp/repo",
                    payload={"command": ["bash", "-lc", 'python3 -c "print(123)"']},
                ),
                state={"repo_initialized": True, "graph_dirty": False},
                constraints={"command_rules": [{"type": "deny_program", "program": "python3"}]},
                action_context={
                    "kind": "run_command",
                    "repo_state": {"state_valid": True},
                    "graph_freshness": {"graph_present": True, "graph_dirty": False},
                    "command_policy_input": {
                        "program": "bash",
                        "effective_program": "python3",
                        "classification": {"family": "python"},
                    },
                },
            )
        )

        self.assertFalse(decision.allowed)
        self.assertIn("python3", decision.reason)


if __name__ == "__main__":
    unittest.main()
