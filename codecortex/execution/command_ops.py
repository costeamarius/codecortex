"""Command execution helpers for the execution layer."""

from __future__ import annotations

import inspect
import os
import subprocess
from typing import Sequence

from .errors import RuntimeBypassError
from .logger import append_operation_log, normalize_log_entry
from .models import ExecutionResult


def run_command_safe(
    repo_path: str,
    command: Sequence[str],
    timeout_seconds: int | None = None,
    agent_id: str | None = None,
    environment: str | None = None,
) -> ExecutionResult:
    caller = inspect.currentframe()
    if caller is None or caller.f_back is None:
        raise RuntimeBypassError("Command execution must be invoked through the runtime executor.")

    caller_module = caller.f_back.f_globals.get("__name__")
    if caller_module not in {"codecortex.execution.executor", "codecortex.runtime.execution_bridge"}:
        raise RuntimeBypassError("Command execution must be invoked through the runtime executor.")

    before_snapshot = _snapshot_python_files(repo_path)
    completed = subprocess.run(
        list(command),
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    after_snapshot = _snapshot_python_files(repo_path)
    changed_python_files = sorted(
        path
        for path in set(before_snapshot) | set(after_snapshot)
        if before_snapshot.get(path) != after_snapshot.get(path)
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
                "changed_python_files": changed_python_files,
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
                "changed_python_files": changed_python_files,
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


def _snapshot_python_files(repo_path: str) -> dict[str, tuple[int, int]]:
    snapshot: dict[str, tuple[int, int]] = {}
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [name for name in dirs if name not in {".git", ".codecortex", "__pycache__"}]
        for filename in files:
            if not filename.endswith(".py"):
                continue
            absolute_path = os.path.join(root, filename)
            relative_path = os.path.relpath(absolute_path, repo_path).replace(os.sep, "/")
            try:
                stat_result = os.stat(absolute_path)
            except OSError:
                continue
            snapshot[relative_path] = (stat_result.st_mtime_ns, stat_result.st_size)
    return snapshot
