"""Repo-bounded file operations for the execution layer."""

from __future__ import annotations

import difflib
import inspect
import os
import shutil
import tempfile
from typing import Tuple

from .errors import PathViolationError, RuntimeBypassError
from .locks import DEFAULT_LOCK_TTL_SECONDS, acquire_write_lock, release_lock
from .logger import append_operation_log, normalize_log_entry
from .models import ExecutionResult
from .validators import validate_content


def resolve_repo_path(repo_path: str, relative_path: str) -> str:
    candidate = os.path.abspath(os.path.join(repo_path, relative_path))
    repo_root = os.path.abspath(repo_path)
    if os.path.commonpath([repo_root, candidate]) != repo_root:
        raise PathViolationError(f"Path escapes repository root: {relative_path}")
    return candidate


def backup_file(path: str) -> str:
    backup_path = f"{path}.bak"
    shutil.copy2(path, backup_path)
    return backup_path


def atomic_write(path: str, content: str) -> None:
    directory = os.path.dirname(path) or "."
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, delete=False) as handle:
        handle.write(content)
        temp_path = handle.name
    os.replace(temp_path, path)


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def build_diff(original: str, updated: str, path: str) -> str:
    diff_lines = difflib.unified_diff(
        original.splitlines(keepends=True),
        updated.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    )
    return "".join(diff_lines)


def write_file_safe(path: str, content: str) -> Tuple[str, str]:
    original = read_file(path)
    backup_path = backup_file(path)
    atomic_write(path, content)
    return original, backup_path


def _require_executor_caller() -> None:
    caller = inspect.currentframe()
    if caller is None or caller.f_back is None or caller.f_back.f_back is None:
        raise RuntimeBypassError("File mutation must be invoked through the runtime executor.")

    caller_module = caller.f_back.f_back.f_globals.get("__name__")
    if caller_module not in {"codecortex.execution.executor", "codecortex.runtime.execution_bridge"}:
        raise RuntimeBypassError("File mutation must be invoked through the runtime executor.")


def edit_file_safe(
    repo_path: str,
    relative_path: str,
    content: str,
    owner: str = "unknown-agent",
    validate: bool = True,
    lock_ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
    environment: str | None = None,
) -> ExecutionResult:
    _require_executor_caller()
    target_path = resolve_repo_path(repo_path, relative_path)
    if not os.path.exists(target_path):
        result = ExecutionResult(
            status="failure",
            action="edit_file",
            details={
                "error_type": "FileNotFoundError",
                "message": f"Target file does not exist: {relative_path}",
                "file": relative_path,
            },
        )
        append_operation_log(
            repo_path,
            normalize_log_entry(
                action="edit_file",
                status=result.status,
                repo=repo_path,
                target=relative_path,
                agent_id=owner,
                environment=environment,
                details=result.details,
            ),
        )
        return result

    acquired, existing_lock = acquire_write_lock(
        repo_path=repo_path,
        resource=relative_path,
        owner=owner,
        ttl_seconds=lock_ttl_seconds,
    )
    if not acquired:
        result = ExecutionResult(
            status="blocked",
            action="edit_file",
            details={
                "resource": relative_path,
                "owner": existing_lock.get("owner") if existing_lock else None,
                "retry_after_seconds": lock_ttl_seconds,
            },
        )
        append_operation_log(
            repo_path,
            normalize_log_entry(
                action="edit_file",
                status=result.status,
                repo=repo_path,
                target=relative_path,
                agent_id=owner,
                environment=environment,
                lock=existing_lock,
                details=result.details,
            ),
        )
        return result

    try:
        original = read_file(target_path)
        validation = validate_content(relative_path, content) if validate else None
        if validation and not validation.passed:
            result = ExecutionResult(
                status="failure",
                action="edit_file",
                details={
                    "error_type": "ValidationError",
                    "message": "Validation failed before commit.",
                    "file": relative_path,
                    "validation": validation.to_dict(),
                },
            )
            append_operation_log(
                repo_path,
                normalize_log_entry(
                    action="edit_file",
                    status=result.status,
                    repo=repo_path,
                    target=relative_path,
                    agent_id=owner,
                    environment=environment,
                    validation=validation.to_dict(),
                    details=result.details,
                ),
            )
            return result

        _, backup_path = write_file_safe(target_path, content)
        diff = build_diff(original, content, relative_path)
        result = ExecutionResult(
            status="success",
            action="edit_file",
            details={
                "file": relative_path,
                "backup_path": backup_path,
                "validation": validation.to_dict() if validation else None,
                "diff": diff,
            },
        )
        append_operation_log(
            repo_path,
            normalize_log_entry(
                action="edit_file",
                status=result.status,
                repo=repo_path,
                target=relative_path,
                agent_id=owner,
                environment=environment,
                validation=validation.to_dict() if validation else None,
                details={
                    "file": relative_path,
                    "backup_path": backup_path,
                },
            ),
        )
        return result
    finally:
        release_lock(repo_path, relative_path)
