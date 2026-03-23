"""Structured operation logging for the execution layer."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from codecortex.project_context import utc_now_iso


def get_logs_dir(repo_path: str) -> str:
    return os.path.join(repo_path, ".codecortex", "logs")


def normalize_log_entry(
    *,
    action: str,
    status: str,
    repo: Optional[str] = None,
    target: Optional[str] = None,
    agent_id: Optional[str] = None,
    environment: Optional[str] = None,
    validation: Optional[Dict[str, Any]] = None,
    lock: Optional[Dict[str, Any]] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    entry: Dict[str, Any] = {
        "timestamp": utc_now_iso(),
        "action": action,
        "status": status,
    }
    if repo is not None:
        entry["repo"] = repo
    if target is not None:
        entry["target"] = target
    if agent_id is not None:
        entry["agent_id"] = agent_id
    if environment is not None:
        entry["environment"] = environment
    if validation is not None:
        entry["validation"] = validation
    if lock is not None:
        entry["lock"] = lock
    if details is not None:
        entry["details"] = details
    return entry


def append_operation_log(repo_path: str, payload: Dict[str, Any]) -> str:
    os.makedirs(get_logs_dir(repo_path), exist_ok=True)
    log_path = os.path.join(get_logs_dir(repo_path), "operations.jsonl")
    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")
    return log_path
