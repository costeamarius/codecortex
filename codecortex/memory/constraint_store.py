"""Constraint store parsing and normalization."""

from __future__ import annotations

from typing import Any, Dict, List


DEFAULT_CONSTRAINT_NOTE = (
    "Keep CodeCortex-generated project memory artifacts under .codecortex/ "
    "(for notes use .codecortex/notes/) and avoid writing them into docs/ "
    "or repository root."
)


def build_default_constraints() -> Dict[str, Any]:
    return {
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
        "constraints": [DEFAULT_CONSTRAINT_NOTE],
    }


def validate_constraints_store(payload: Any) -> List[str]:
    issues: List[str] = []
    if not isinstance(payload, dict):
        issues.append("constraints payload must be a JSON object")
        return issues

    path_rule = payload.get("path_write_rule")
    if path_rule is not None and _normalize_path_rule(path_rule) is None:
        issues.append("path_write_rule is invalid")

    path_rules = payload.get("path_write_rules")
    if path_rules is not None:
        if not isinstance(path_rules, list):
            issues.append("path_write_rules must be a list")
        else:
            for rule in path_rules:
                if _normalize_path_rule(rule) is None:
                    issues.append("path_write_rules contains an invalid rule")
                    break

    command_rule = payload.get("command_rule")
    if command_rule is not None and _normalize_command_rule(command_rule) is None:
        issues.append("command_rule is invalid")

    command_rules = payload.get("command_rules")
    if command_rules is not None:
        if not isinstance(command_rules, list):
            issues.append("command_rules must be a list")
        else:
            for rule in command_rules:
                if _normalize_command_rule(rule) is None:
                    issues.append("command_rules contains an invalid rule")
                    break

    constraints = payload.get("constraints")
    if constraints is not None and not isinstance(constraints, list):
        issues.append("constraints must be a list")

    return issues


def normalize_constraints_store(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return build_default_constraints()

    normalized = build_default_constraints()
    normalized["path_write_rules"] = []
    normalized["command_rules"] = []
    normalized["constraints"] = []

    schema_version = payload.get("schema_version")
    normalized["schema_version"] = schema_version if isinstance(schema_version, str) and schema_version.strip() else "1.0"
    normalized["require_fresh_graph"] = bool(payload.get("require_fresh_graph", False))

    path_rule = _normalize_path_rule(payload.get("path_write_rule"))
    if path_rule:
        normalized["path_write_rules"].append(path_rule)

    path_rules = payload.get("path_write_rules")
    if isinstance(path_rules, list):
        for rule in path_rules:
            normalized_rule = _normalize_path_rule(rule)
            if normalized_rule:
                normalized["path_write_rules"].append(normalized_rule)

    command_rule = _normalize_command_rule(payload.get("command_rule"))
    if command_rule:
        normalized["command_rules"].append(command_rule)

    command_rules = payload.get("command_rules")
    if isinstance(command_rules, list):
        for rule in command_rules:
            normalized_rule = _normalize_command_rule(rule)
            if normalized_rule:
                normalized["command_rules"].append(normalized_rule)

    constraints = payload.get("constraints")
    if isinstance(constraints, list):
        normalized["constraints"] = [item for item in constraints if isinstance(item, str) and item.strip()]

    return normalized


def _normalize_path_rule(rule: Any) -> Dict[str, Any] | None:
    if not isinstance(rule, dict):
        return None

    mode = rule.get("mode")
    pattern = rule.get("pattern")
    if mode not in {"deny", "allow"}:
        return None
    if not isinstance(pattern, str) or not pattern.strip():
        return None

    normalized = {
        "mode": mode,
        "pattern": pattern,
    }
    reason = rule.get("reason")
    if isinstance(reason, str) and reason.strip():
        normalized["reason"] = reason
    return normalized


def _normalize_command_rule(rule: Any) -> Dict[str, Any] | None:
    if not isinstance(rule, dict):
        return None

    rule_type = rule.get("type")
    if rule_type == "deny_program":
        program = rule.get("program")
        if not isinstance(program, str) or not program.strip():
            return None
        normalized = {"type": "deny_program", "program": program}
    elif rule_type == "deny_family":
        family_name = rule.get("family_name")
        if not isinstance(family_name, str) or not family_name.strip():
            return None
        normalized = {"type": "deny_family", "family_name": family_name}
    else:
        return None

    reason = rule.get("reason")
    if isinstance(reason, str) and reason.strip():
        normalized["reason"] = reason
    return normalized
