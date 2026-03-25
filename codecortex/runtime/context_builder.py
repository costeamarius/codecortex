"""Runtime context loading from repo-local memory."""

from __future__ import annotations

import os
import shlex
from typing import Any, Dict, List

from codecortex.graph_context import compute_file_context_from_graph
from codecortex.memory.constraint_store import normalize_constraints_store
from codecortex.memory.decision_store import list_decisions, query_decisions
from codecortex.memory.state_store import (
    build_initial_runtime_state,
    build_state_paths,
    is_valid_runtime_state,
)
from codecortex.project_context import read_json
from codecortex.runtime.models import ActionRequest, RuntimeContext
from codecortex.semantics_store import merge_graph_with_semantics, normalize_semantics_store


class ContextBuilder:
    """Build a runtime context from the bound repository state."""

    def build(self, repo_root: str, request: ActionRequest) -> RuntimeContext:
        paths = build_state_paths(repo_root)
        self._active_state_dir = paths["dir"]
        semantics = normalize_semantics_store(read_json(paths["semantics"]))
        raw_graph = self._load_graph(paths["graph"])
        decisions = self._load_decisions(paths["decisions"])
        runtime_state, state_valid = self._load_runtime_state(paths["state"])
        constraints = normalize_constraints_store(read_json(paths["constraints"]))
        merged_graph = merge_graph_with_semantics(raw_graph, semantics)

        return RuntimeContext(
            repo=repo_root,
            state_dir=paths["dir"],
            request=ActionRequest(
                action=request.action,
                repo=repo_root,
                payload=dict(request.payload),
                agent_id=request.agent_id,
                environment=request.environment,
            ),
            meta=read_json(paths["meta"]) or {},
            state=runtime_state,
            graph=merged_graph,
            semantics=semantics,
            constraints=constraints,
            decisions=decisions,
            action_context=self._build_action_context(
                repo_root=repo_root,
                request=request,
                state=runtime_state,
                state_valid=state_valid,
                constraints=constraints,
                graph=merged_graph,
                semantics=semantics,
                decisions=decisions,
            ),
        )

    def _load_graph(self, path: str) -> Dict[str, Any]:
        payload = read_json(path)
        if not isinstance(payload, dict):
            return {}
        return payload

    def _load_runtime_state(self, state_path: str) -> tuple[Dict[str, Any], bool]:
        payload = read_json(state_path)
        if is_valid_runtime_state(payload):
            return payload, True

        invalid_state = build_initial_runtime_state()
        invalid_state["repo_initialized"] = False
        invalid_state["graph_dirty"] = False
        return invalid_state, False

    def _load_decisions(self, path: str) -> List[Dict[str, Any]]:
        return list_decisions(path)

    def _build_action_context(
        self,
        repo_root: str,
        request: ActionRequest,
        state: Dict[str, Any],
        state_valid: bool,
        constraints: Dict[str, Any],
        graph: Dict[str, Any],
        semantics: Dict[str, Any],
        decisions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        graph_present = self._graph_present(graph)
        graph_dirty = bool(state.get("graph_dirty"))

        if request.action == "run_command":
            return self._build_run_command_context(
                request=request,
                state=state,
                state_valid=state_valid,
                constraints=constraints,
                graph_present=graph_present,
                graph_dirty=graph_dirty,
            )

        if request.action != "edit_file":
            return {}

        file_path = self._normalize_request_file_path(repo_root, request.payload.get("file"))
        if not isinstance(file_path, str) or not file_path.strip():
            return {
                "kind": "edit_file",
                "file": None,
                "file_found": False,
                "repo_state": {
                    "repo_initialized": bool(state.get("repo_initialized")),
                    "state_valid": state_valid,
                    "graph_dirty": graph_dirty,
                    "last_scan_at": state.get("last_scan_at"),
                    "last_scan_commit": state.get("last_scan_commit"),
                },
            }

        file_context = compute_file_context_from_graph(repo_root, graph, file_path)
        if "file_found" not in file_context:
            file_context["file_found"] = False
        targets = self._build_edit_targets(file_context)
        relevant_assertions = self._filter_relevant_assertions(
            semantics.get("assertions") or [],
            targets,
        )
        recent_decisions = self._filter_relevant_decisions(decisions, targets)

        return {
            "kind": "edit_file",
            "repo_state": {
                "repo_initialized": bool(state.get("repo_initialized")),
                "state_valid": state_valid,
                "graph_dirty": graph_dirty,
                "last_scan_at": state.get("last_scan_at"),
                "last_scan_commit": state.get("last_scan_commit"),
            },
            "graph_freshness": {
                "graph_present": graph_present,
                "graph_dirty": graph_dirty,
                "graph_status": "dirty" if graph_dirty else ("fresh" if graph_present else "missing"),
            },
            **file_context,
            "relevant_semantic_assertions": relevant_assertions,
            "recent_decisions": recent_decisions,
        }

    def _build_run_command_context(
        self,
        request: ActionRequest,
        state: Dict[str, Any],
        state_valid: bool,
        constraints: Dict[str, Any],
        graph_present: bool,
        graph_dirty: bool,
    ) -> Dict[str, Any]:
        command = request.payload.get("command")
        if isinstance(command, (list, tuple)):
            argv = [str(part) for part in command]
        else:
            argv = []

        timeout_seconds = request.payload.get("timeout_seconds")
        effective_command = self._extract_effective_command(argv)
        effective_argv = effective_command["argv"]

        return {
            "kind": "run_command",
            "repo_state": {
                "repo_initialized": bool(state.get("repo_initialized")),
                "state_valid": state_valid,
                "graph_dirty": graph_dirty,
                "last_scan_at": state.get("last_scan_at"),
                "last_scan_commit": state.get("last_scan_commit"),
            },
            "graph_freshness": {
                "graph_present": graph_present,
                "graph_dirty": graph_dirty,
                "graph_status": "dirty" if graph_dirty else ("fresh" if graph_present else "missing"),
            },
            "command_policy_input": {
                "argv": argv,
                "argc": len(argv),
                "program": argv[0] if argv else None,
                "effective_argv": effective_argv,
                "effective_argc": len(effective_argv),
                "effective_program": effective_argv[0] if effective_argv else None,
                "wrapper_program": argv[0] if argv else None,
                "timeout_seconds": timeout_seconds,
                "environment": request.environment,
                "agent_id": request.agent_id,
                "classification": self._classify_command(effective_argv),
                "wrapper_classification": self._classify_command(argv),
            },
            "relevant_command_policy_rules": self._extract_command_policy_rules(constraints),
        }

    def _graph_present(self, graph: Dict[str, Any]) -> bool:
        return bool(graph.get("nodes") or graph.get("edges") or graph.get("git_commit"))

    def _build_edit_targets(self, file_context: Dict[str, Any]) -> set[str]:
        targets = set()
        normalized_file = file_context.get("file")
        if isinstance(normalized_file, str) and normalized_file:
            targets.add(normalized_file)
            targets.add(f"file:{normalized_file}")
            targets.add(os.path.basename(normalized_file))

        module_name = file_context.get("module_name")
        if isinstance(module_name, str) and module_name:
            targets.add(module_name)
            targets.add(f"module:{module_name}")

        file_node_id = file_context.get("file_node_id")
        if isinstance(file_node_id, str) and file_node_id:
            targets.add(file_node_id)

        for symbol in file_context.get("symbols_defined") or []:
            symbol_id = symbol.get("id")
            if isinstance(symbol_id, str) and symbol_id:
                targets.add(symbol_id)
            qualname = symbol.get("qualname")
            if isinstance(qualname, str) and qualname:
                targets.add(qualname)
            name = symbol.get("name")
            if isinstance(name, str) and name:
                targets.add(name)

        return targets

    def _filter_relevant_assertions(
        self,
        assertions: List[Dict[str, Any]],
        targets: set[str],
    ) -> List[Dict[str, Any]]:
        relevant = []
        for assertion in assertions:
            if not isinstance(assertion, dict):
                continue
            values = self._collect_strings(assertion)
            if values & targets:
                relevant.append(assertion)
        return relevant

    def _filter_relevant_decisions(
        self,
        decisions: List[Dict[str, Any]],
        targets: set[str],
    ) -> List[Dict[str, Any]]:
        if not targets:
            return []

        state_dir = getattr(self, "_active_state_dir", None)
        if isinstance(state_dir, str) and state_dir:
            return query_decisions(os.path.join(state_dir, "decisions.jsonl"), targets, limit=10)

        matched = []
        for decision in decisions:
            if not isinstance(decision, dict):
                continue
            values = self._collect_strings(decision)
            if values & targets:
                matched.append(decision)
        return matched[-10:]

    def _collect_strings(self, payload: Any) -> set[str]:
        values = set()
        self._collect_strings_into(payload, values)
        return values

    def _collect_strings_into(self, payload: Any, values: set[str]) -> None:
        if isinstance(payload, str):
            values.add(payload)
            return
        if isinstance(payload, dict):
            for value in payload.values():
                self._collect_strings_into(value, values)
            return
        if isinstance(payload, list):
            for item in payload:
                self._collect_strings_into(item, values)

    def _classify_command(self, argv: List[str]) -> Dict[str, Any]:
        if not argv:
            return {
                "family": "unknown",
                "is_python": False,
                "is_test_command": False,
                "is_package_manager": False,
                "is_shell_wrapper": False,
            }

        program = argv[0]
        joined = " ".join(argv)
        python_programs = {"python", "python3", "pytest"}
        package_managers = {"pip", "pip3", "poetry", "uv", "npm", "pnpm", "yarn"}
        shell_wrappers = {"sh", "bash", "zsh", "fish"}
        is_python = (
            program in python_programs
            or program.endswith("python")
            or program.endswith("python3")
        )
        is_test_command = "pytest" in argv or "unittest" in joined
        is_package_manager = program in package_managers
        is_shell_wrapper = program in shell_wrappers

        if is_test_command:
            family = "test"
        elif is_python:
            family = "python"
        elif is_package_manager:
            family = "package_manager"
        elif is_shell_wrapper:
            family = "shell"
        else:
            family = "generic"

        return {
            "family": family,
            "is_python": is_python,
            "is_test_command": is_test_command,
            "is_package_manager": is_package_manager,
            "is_shell_wrapper": is_shell_wrapper,
        }

    def _extract_command_policy_rules(self, constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
        rules = []

        command_rules = constraints.get("command_rules")
        if isinstance(command_rules, list):
            for rule in command_rules:
                if isinstance(rule, dict):
                    rules.append(rule)

        require_fresh_graph = constraints.get("require_fresh_graph")
        if require_fresh_graph is not None:
            rules.append(
                {
                    "type": "require_fresh_graph",
                    "value": bool(require_fresh_graph),
                }
            )

        constraints_list = constraints.get("constraints")
        if isinstance(constraints_list, list):
            for item in constraints_list:
                if isinstance(item, str) and "command" in item.lower():
                    rules.append({"type": "legacy_constraint", "value": item})

        return rules

    def _normalize_request_file_path(self, repo_root: str, file_path: Any) -> Any:
        if not isinstance(file_path, str) or not file_path.strip():
            return file_path

        normalized = file_path
        if os.path.isabs(file_path):
            repo_abs = os.path.abspath(repo_root)
            file_abs = os.path.abspath(file_path)
            try:
                if os.path.commonpath([repo_abs, file_abs]) == repo_abs:
                    normalized = os.path.relpath(file_abs, repo_abs)
            except ValueError:
                normalized = file_path

        normalized = os.path.normpath(normalized)
        if normalized == ".":
            return ""
        return normalized.replace(os.sep, "/")

    def _extract_effective_command(self, argv: List[str]) -> Dict[str, Any]:
        if len(argv) == 3 and argv[0] in {"sh", "bash", "zsh", "fish"} and argv[1] == "-lc":
            try:
                parsed = shlex.split(argv[2])
            except ValueError:
                parsed = []
            if parsed:
                return {
                    "argv": parsed,
                    "source": "shell_wrapper",
                    "shell_program": argv[0],
                }

        return {
            "argv": argv,
            "source": "direct",
            "shell_program": None,
        }
