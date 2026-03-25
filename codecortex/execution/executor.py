"""Internal deterministic executor used by the runtime kernel.

This module is not the public agent boundary. External callers should enter
through the runtime gateway/kernel and let the runtime decide when execution
is invoked.
"""

from __future__ import annotations

import inspect
import warnings

from .errors import RuntimeBypassError
from .command_ops import run_command_safe
from .file_ops import edit_file_safe
from .logger import append_operation_log, normalize_log_entry
from .models import ExecutionAction, ExecutionResult


SUPPORTED_ACTIONS = {"edit_file", "run_command"}
SUPPORTED_STATUSES = {"success", "failure", "blocked", "not_implemented"}
ALLOWED_RUNTIME_CALLERS = {
    "codecortex.runtime.kernel",
    "codecortex.runtime.execution_bridge",
}


def _require_runtime_kernel_caller() -> None:
    caller = inspect.currentframe()
    if caller is None or caller.f_back is None or caller.f_back.f_back is None:
        raise RuntimeBypassError("Execution must be invoked through RuntimeKernel.handle_action().")

    caller_module = caller.f_back.f_back.f_globals.get("__name__")
    if caller_module not in ALLOWED_RUNTIME_CALLERS:
        raise RuntimeBypassError(
            "Execution must be invoked through the runtime kernel execution path."
        )


def execute_action(action: ExecutionAction) -> ExecutionResult:
    """Deprecated internal executor entrypoint.

    External callers should use ``codecortex.runtime.AgentGateway`` or the
    repo-local ``cortex action`` CLI surface instead of calling this function
    directly.
    """
    warnings.warn(
        "codecortex.execution.executor.execute_action() is deprecated as a public surface. "
        "Use AgentGateway.handle_action() or `cortex action` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    _require_runtime_kernel_caller()

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
