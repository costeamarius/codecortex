"""Minimal deterministic action executor."""

from __future__ import annotations

from .command_ops import run_command_safe
from .file_ops import edit_file_safe
from .logger import append_operation_log, normalize_log_entry
from .models import ExecutionAction, ExecutionResult


SUPPORTED_ACTIONS = {"edit_file", "run_command"}
SUPPORTED_STATUSES = {"success", "failure", "blocked", "not_implemented"}


def blocked_result(action: str, resource: str, owner: str | None = None, retry_after_seconds: int = 10) -> ExecutionResult:
    return ExecutionResult(
        status="blocked",
        action=action,
        details={
            "resource": resource,
            "owner": owner,
            "retry_after_seconds": retry_after_seconds,
        },
    )


def failure_result(action: str, error_type: str, message: str, **details) -> ExecutionResult:
    return ExecutionResult(
        status="failure",
        action=action,
        details={
            "error_type": error_type,
            "message": message,
            **details,
        },
    )


def execute_action(action: ExecutionAction) -> ExecutionResult:
    """Execute a structured action through the repo-local execution layer."""
    if action.action not in SUPPORTED_ACTIONS:
        result = ExecutionResult(
            status="not_implemented",
            action=action.action,
            details={
                "message": f"Unsupported action '{action.action}' for execution v1.",
                "repo": action.repo,
                "supported_actions": sorted(SUPPORTED_ACTIONS),
            },
        )
        append_operation_log(
            action.repo,
            normalize_log_entry(
                action=action.action,
                status=result.status,
                repo=action.repo,
                agent_id=action.agent_id,
                environment=action.environment,
                details=result.details,
            ),
        )
        return result

    if action.action == "edit_file":
        payload = action.payload
        return edit_file_safe(
            repo_path=action.repo,
            relative_path=payload["file"],
            content=payload["content"],
            owner=action.agent_id or "unknown-agent",
            validate=payload.get("validate", True),
            lock_ttl_seconds=payload.get("lock_ttl_seconds", 30),
            environment=action.environment,
        )

    if action.action == "run_command":
        payload = action.payload
        return run_command_safe(
            repo_path=action.repo,
            command=payload["command"],
            timeout_seconds=payload.get("timeout_seconds"),
            agent_id=action.agent_id,
            environment=action.environment,
        )

    result = ExecutionResult(
        status="not_implemented",
        action=action.action,
        details={
            "message": f"Action '{action.action}' is defined in the v1 contract but not implemented yet.",
            "repo": action.repo,
        },
    )
    append_operation_log(
        action.repo,
        normalize_log_entry(
            action=action.action,
            status=result.status,
            repo=action.repo,
            agent_id=action.agent_id,
            environment=action.environment,
            details=result.details,
        ),
    )
    return result
