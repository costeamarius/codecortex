"""Runtime-controlled bridge into the low-level execution layer."""

from __future__ import annotations

import inspect

from codecortex.execution.command_ops import run_command_safe
from codecortex.execution.file_ops import edit_file_safe
from codecortex.execution.models import ExecutionResult
from codecortex.execution.errors import RuntimeBypassError
from codecortex.runtime.models import RuntimeContext


class ExecutionBridge:
    """Convert approved runtime context into an execution-layer action."""

    def execute(self, context: RuntimeContext) -> ExecutionResult:
        self._require_kernel_caller()
        request = context.request
        if request is None:
            raise ValueError("RuntimeContext.request is required for execution.")

        if request.action == "edit_file":
            return edit_file_safe(
                repo_path=context.repo,
                relative_path=request.payload["file"],
                content=request.payload["content"],
                owner=request.agent_id or "unknown-agent",
                validate=request.payload.get("validate", True),
                lock_ttl_seconds=request.payload.get("lock_ttl_seconds", 30),
                environment=request.environment,
            )
        if request.action == "run_command":
            return run_command_safe(
                repo_path=context.repo,
                command=request.payload["command"],
                timeout_seconds=request.payload.get("timeout_seconds"),
                agent_id=request.agent_id,
                environment=request.environment,
            )

        raise ValueError(f"Unsupported runtime action for execution bridge: {request.action}")

    def _require_kernel_caller(self) -> None:
        caller = inspect.currentframe()
        if caller is None or caller.f_back is None or caller.f_back.f_back is None:
            raise RuntimeBypassError("Execution bridge must be invoked through RuntimeKernel.handle_action().")

        caller_module = caller.f_back.f_back.f_globals.get("__name__")
        if caller_module != "codecortex.runtime.kernel":
            raise RuntimeBypassError("Execution bridge must be invoked through RuntimeKernel.handle_action().")
