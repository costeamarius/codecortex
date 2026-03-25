"""Minimal runtime policy evaluation."""

from __future__ import annotations

import os
from fnmatch import fnmatch
from typing import Any, Dict, List, Tuple

from codecortex.agent_operating_model import is_participating_agent
from codecortex.runtime.models import PolicyDecision, RuntimeContext


class PolicyEngine:
    """Evaluate first-pass repo state, path, and command rules."""

    def evaluate(self, context: RuntimeContext) -> PolicyDecision:
        request = context.request
        if request is None:
            return PolicyDecision(
                allowed=False,
                reason="Runtime policy requires a bound action request.",
                violations=["missing_request"],
                details={"stage": "policy_engine"},
            )

        violations: List[str] = []
        warnings: List[str] = []
        matched_rules: List[Dict[str, Any]] = []

        repo_state_violation, repo_state_warnings, repo_rules = self._evaluate_repo_state_rules(context)
        violations.extend(repo_state_violation)
        warnings.extend(repo_state_warnings)
        matched_rules.extend(repo_rules)

        identity_violations, identity_rules = self._evaluate_agent_identity_rules(context)
        violations.extend(identity_violations)
        matched_rules.extend(identity_rules)

        if request.action == "edit_file":
            path_violations, path_rules = self._evaluate_path_rules(context)
            violations.extend(path_violations)
            matched_rules.extend(path_rules)

        if request.action == "run_command":
            command_violations, command_rules = self._evaluate_command_rules(context)
            violations.extend(command_violations)
            matched_rules.extend(command_rules)

        if violations:
            return PolicyDecision(
                allowed=False,
                reason=violations[0],
                violations=violations,
                details={
                    "stage": "policy_engine",
                    "matched_rules": matched_rules,
                    "action": request.action,
                },
            )

        return PolicyDecision(
            allowed=True,
            reason="allowed by runtime policy",
            details={
                "stage": "policy_engine",
                "matched_rules": matched_rules,
                "action": request.action,
                "warnings": warnings,
            },
        )

    def _evaluate_agent_identity_rules(
        self, context: RuntimeContext
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        violations: List[str] = []
        matched_rules: List[Dict[str, Any]] = []
        request = context.request
        if request is None:
            return violations, matched_rules

        participating_environment = is_participating_agent(request.environment)
        mutating_action = self._is_mutating_action(request.action)

        if participating_environment:
            matched_rules.append(
                {
                    "family": "agent_identity",
                    "type": "participating_environment",
                    "environment": request.environment,
                    "value": True,
                }
            )

        if not (participating_environment and mutating_action):
            return violations, matched_rules

        matched_rules.append(
            {
                "family": "agent_identity",
                "type": "require_agent_id_for_mutation",
                "action": request.action,
                "environment": request.environment,
                "value": True,
            }
        )
        if not self._has_agent_identity(request.agent_id):
            violations.append(
                f"Mutating action '{request.action}' from participating environment "
                f"'{request.environment}' requires agent_id."
            )

        return violations, matched_rules

    def _evaluate_repo_state_rules(
        self, context: RuntimeContext
    ) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
        violations: List[str] = []
        warnings: List[str] = []
        matched_rules: List[Dict[str, Any]] = []
        state = context.state or {}
        constraints = context.constraints or {}
        request = context.request
        repo_state = (context.action_context or {}).get("repo_state") or {}

        state_valid = repo_state.get("state_valid")
        if state_valid is False:
            violations.append("Repository runtime state is missing or invalid.")
            matched_rules.append({"family": "repo_state", "type": "state_valid", "value": False})

        if not state.get("repo_initialized", False):
            violations.append("Repository runtime state is not initialized.")
            matched_rules.append({"family": "repo_state", "type": "repo_initialized", "value": False})

        graph_freshness = self._get_graph_freshness(context)
        graph_present = graph_freshness.get("graph_present")
        graph_dirty = graph_freshness.get("graph_dirty")
        if graph_present is not None:
            matched_rules.append({"family": "repo_state", "type": "graph_present", "value": bool(graph_present)})
        if graph_dirty is not None:
            matched_rules.append({"family": "repo_state", "type": "graph_dirty", "value": bool(graph_dirty)})

        if request and request.action == "edit_file" and graph_present is False:
            warnings.append("Edit action is running without a repository graph; graph-backed context is degraded.")

        require_fresh_graph = bool(constraints.get("require_fresh_graph"))
        if require_fresh_graph:
            matched_rules.append({"family": "repo_state", "type": "require_fresh_graph", "value": True})

            if request and self._action_requires_graph_state(request.action):
                if not graph_present:
                    violations.append(
                        f"Action '{request.action}' requires a graph, but no graph is present."
                    )
                elif graph_dirty:
                    violations.append(
                        f"Action '{request.action}' requires a fresh graph, but the graph is dirty."
                    )

        return violations, warnings, matched_rules

    def _evaluate_path_rules(
        self, context: RuntimeContext
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        violations: List[str] = []
        matched_rules: List[Dict[str, Any]] = []
        request = context.request
        if request is None:
            return violations, matched_rules

        relative_path = self._normalize_policy_path(context.repo, request.payload.get("file"))
        if not isinstance(relative_path, str) or not relative_path.strip():
            return violations, matched_rules

        for rule in self._iter_path_rules(context.constraints or {}):
            matched_rules.append({"family": "path", **rule})
            if rule.get("mode") != "deny":
                continue

            pattern = rule.get("pattern")
            if isinstance(pattern, str) and fnmatch(relative_path, pattern):
                violations.append(f"Write blocked by path rule for '{pattern}'.")

        return violations, matched_rules

    def _evaluate_command_rules(
        self, context: RuntimeContext
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        violations: List[str] = []
        matched_rules: List[Dict[str, Any]] = []
        command_input = (context.action_context or {}).get("command_policy_input") or {}
        program = command_input.get("effective_program") or command_input.get("program")
        classification = command_input.get("classification") or {}

        for rule in self._iter_command_rules(context.constraints or {}):
            matched_rules.append({"family": "command", **rule})
            rule_type = rule.get("type")
            if rule_type == "deny_program" and program == rule.get("program"):
                violations.append(f"Command program '{program}' is blocked by policy.")
            elif rule_type == "deny_family" and classification.get("family") == rule.get("family_name"):
                violations.append(
                    f"Command family '{classification.get('family')}' is blocked by policy."
                )

        return violations, matched_rules

    def _iter_path_rules(self, constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
        rules: List[Dict[str, Any]] = []
        multi_rules = constraints.get("path_write_rules")
        if isinstance(multi_rules, list):
            for rule in multi_rules:
                if isinstance(rule, dict):
                    rules.append(rule)

        return rules

    def _iter_command_rules(self, constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
        rules: List[Dict[str, Any]] = []
        multi_rules = constraints.get("command_rules")
        if isinstance(multi_rules, list):
            for rule in multi_rules:
                if isinstance(rule, dict):
                    rules.append(rule)

        return rules

    def _get_graph_freshness(self, context: RuntimeContext) -> Dict[str, Any]:
        graph_freshness = (context.action_context or {}).get("graph_freshness")
        if isinstance(graph_freshness, dict):
            return graph_freshness

        graph = context.graph or {}
        state = context.state or {}
        graph_present = bool(graph.get("nodes") or graph.get("edges") or graph.get("git_commit"))
        graph_dirty = bool(state.get("graph_dirty"))
        return {
            "graph_present": graph_present,
            "graph_dirty": graph_dirty,
            "graph_status": "dirty" if graph_dirty else ("fresh" if graph_present else "missing"),
        }

    def _action_requires_graph_state(self, action: str) -> bool:
        return action in {"edit_file", "run_command"}

    def _is_mutating_action(self, action: str) -> bool:
        return action in {"edit_file", "run_command"}

    def _has_agent_identity(self, agent_id: Any) -> bool:
        return isinstance(agent_id, str) and bool(agent_id.strip())

    def _normalize_policy_path(self, repo_root: str, file_path: Any) -> Any:
        if not isinstance(file_path, str) or not file_path.strip():
            return file_path

        normalized = file_path
        if repo_root and isinstance(repo_root, str) and file_path.startswith("/"):
            try:
                repo_abs = os.path.abspath(repo_root)
                file_abs = os.path.abspath(file_path)
                if os.path.commonpath([repo_abs, file_abs]) == repo_abs:
                    normalized = os.path.relpath(file_abs, repo_abs)
            except ValueError:
                normalized = file_path

        normalized = os.path.normpath(normalized)
        if normalized == ".":
            return ""
        return normalized.replace(os.sep, "/")
