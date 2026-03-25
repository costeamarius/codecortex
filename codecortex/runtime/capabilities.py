"""Computed runtime capability snapshot."""

from __future__ import annotations

from typing import Any, Dict, List

from codecortex.execution.executor import SUPPORTED_ACTIONS
from codecortex.memory.constraint_store import normalize_constraints_store, validate_constraints_store
from codecortex.memory.detection import detect_repo_binding
from codecortex.memory.state_store import build_state_paths, is_valid_runtime_state, read_json_file


MEMORY_CLI_COMMANDS = [
    "init",
    "init-agent",
    "scan",
    "update",
    "status",
    "query",
    "context",
    "symbol",
    "impact",
    "remember",
    "feature",
    "semantics",
    "benchmark",
]

EXECUTION_CLI_COMMANDS = ["edit-file", "run-command"]
CANONICAL_RUNTIME_INGRESS = {
    "cli_command": "cortex action",
    "request_modes": ["--stdin", "--request-file"],
    "structured_json_required": True,
}


def build_capabilities_snapshot(path: str) -> Dict[str, Any]:
    binding = detect_repo_binding(path)
    paths = build_state_paths(binding.repo_root)

    raw_state = read_json_file(paths["state"])
    raw_graph = read_json_file(paths["graph"])
    raw_constraints = read_json_file(paths["constraints"])

    state_valid = is_valid_runtime_state(raw_state)
    repo_initialized = bool(binding.enabled and state_valid and raw_state.get("repo_initialized"))
    graph_present = _graph_present(raw_graph)
    graph_dirty = bool(raw_state.get("graph_dirty")) if state_valid else False
    constraints_loaded = isinstance(raw_constraints, dict)
    constraint_issues = validate_constraints_store(raw_constraints) if raw_constraints is not None else []
    normalized_constraints = normalize_constraints_store(raw_constraints)
    supported_actions = sorted(SUPPORTED_ACTIONS)
    warnings = _build_warnings(
        codecortex_enabled=binding.enabled,
        state_valid=state_valid,
        repo_initialized=repo_initialized,
        graph_present=graph_present,
        graph_dirty=graph_dirty,
        constraints_loaded=constraints_loaded,
        constraints_valid=not constraint_issues,
    )

    return {
        "codecortex_enabled": binding.enabled,
        "repo": binding.repo_root,
        "state_dir": binding.state_dir,
        "meta_path": binding.meta_path,
        "markers": binding.markers,
        "execution": {
            "cli_commands": EXECUTION_CLI_COMMANDS,
            "supported_actions": supported_actions,
            "deterministic_execution_v1": True,
            "deprecated_public_surfaces": {
                "cli_commands": EXECUTION_CLI_COMMANDS,
                "reason": "Use the structured runtime ingress instead of direct mutation-specific CLI entrypoints.",
            },
        },
        "memory": {
            "cli_commands": MEMORY_CLI_COMMANDS,
        },
        "runtime": {
            "ingress": CANONICAL_RUNTIME_INGRESS,
            "repo_initialized": repo_initialized,
            "state_loaded": state_valid,
            "graph_present": graph_present,
            "graph_dirty": graph_dirty,
            "graph_status": _graph_status(graph_present, graph_dirty),
            "constraints_loaded": constraints_loaded,
            "constraint_issues": constraint_issues,
            "constraints_active": _constraints_active(normalized_constraints),
            "supported_actions": supported_actions,
            "readiness": {
                "runtime_actions_available": bool(binding.enabled and repo_initialized),
                "edit_file": bool(binding.enabled and repo_initialized),
                "run_command": bool(binding.enabled and repo_initialized),
                "graph_context_available": graph_present,
                "graph_context_fresh": bool(graph_present and not graph_dirty),
            },
            "warnings": warnings,
        },
    }


def _graph_present(graph: Dict[str, Any] | None) -> bool:
    if not isinstance(graph, dict):
        return False
    return bool(graph.get("nodes") or graph.get("edges") or graph.get("git_commit"))


def _graph_status(graph_present: bool, graph_dirty: bool) -> str:
    if not graph_present:
        return "missing"
    if graph_dirty:
        return "dirty"
    return "fresh"


def _constraints_active(constraints: Dict[str, Any]) -> Dict[str, Any]:
    path_rules = constraints.get("path_write_rules") or []
    command_rules = constraints.get("command_rules") or []
    require_fresh_graph = bool(constraints.get("require_fresh_graph"))
    return {
        "path_write_rules": len(path_rules),
        "command_rules": len(command_rules),
        "require_fresh_graph": require_fresh_graph,
        "loaded_constraint_notes": len(constraints.get("constraints") or []),
    }


def _build_warnings(
    *,
    codecortex_enabled: bool,
    state_valid: bool,
    repo_initialized: bool,
    graph_present: bool,
    graph_dirty: bool,
    constraints_loaded: bool,
    constraints_valid: bool,
) -> List[str]:
    warnings: List[str] = []
    if not codecortex_enabled:
        warnings.append("Repository is not CodeCortex-enabled; runtime actions are unavailable.")
    elif not state_valid:
        warnings.append("Runtime state is missing or invalid; repo initialization is incomplete.")
    elif not repo_initialized:
        warnings.append("Runtime state reports repo_initialized=false; runtime actions are blocked by policy.")

    if not graph_present:
        warnings.append("Repository graph is missing; graph-backed context is unavailable.")
    elif graph_dirty:
        warnings.append("Repository graph is dirty; graph-dependent actions may be degraded or blocked.")

    if not constraints_loaded:
        warnings.append("constraints.json is missing or invalid; default in-memory policy constraints are active.")
    elif not constraints_valid:
        warnings.append("constraints.json contains invalid entries; unsupported rules were ignored.")

    return warnings
