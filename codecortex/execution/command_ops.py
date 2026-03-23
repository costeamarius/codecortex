"""Command execution helpers for the execution layer."""

from __future__ import annotations

import subprocess
from typing import Sequence

from .logger import append_operation_log, normalize_log_entry
from .models import ExecutionResult


def run_command_safe(
    repo_path: str,
    command: Sequence[str],
    timeout_seconds: int | None = None,
    agent_id: str | None = None,
    environment: str | None = None,
) -> ExecutionResult:
    completed = subprocess.run(
        list(command),
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )

    if completed.returncode != 0:
        result = ExecutionResult(
            status="failure",
            action="run_command",
            details={
                "error_type": "CommandExecutionError",
                "message": "Command execution failed.",
                "command": list(command),
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
        )
    else:
        result = ExecutionResult(
            status="success",
            action="run_command",
            details={
                "command": list(command),
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
        )

    append_operation_log(
        repo_path,
        normalize_log_entry(
            action="run_command",
            status=result.status,
            repo=repo_path,
            target="<command>",
            agent_id=agent_id,
            environment=environment,
            details=result.details,
        ),
    )
    return result
