"""Minimal write-lock handling for execution v1."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from codecortex.project_context import utc_now_iso


DEFAULT_LOCK_TTL_SECONDS = 30


def get_locks_dir(repo_path: str) -> str:
    return os.path.join(repo_path, ".codecortex", "locks")


def lock_path_for(repo_path: str, resource: str) -> str:
    safe_name = resource.replace("/", "__").replace("\\", "__") + ".lock.json"
    return os.path.join(get_locks_dir(repo_path), safe_name)


def read_lock(repo_path: str, resource: str) -> Optional[dict]:
    path = lock_path_for(repo_path, resource)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_lock(repo_path: str, payload: dict) -> str:
    os.makedirs(get_locks_dir(repo_path), exist_ok=True)
    path = lock_path_for(repo_path, payload["resource"])
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return path


def release_lock(repo_path: str, resource: str) -> None:
    path = lock_path_for(repo_path, resource)
    if os.path.exists(path):
        os.remove(path)


def compute_expiry(ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS) -> str:
    expiry = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    return expiry.isoformat()


def is_lock_expired(lock_payload: dict) -> bool:
    expires_at = lock_payload.get("expires_at")
    if not expires_at:
        return False
    try:
        expiry = datetime.fromisoformat(expires_at)
    except ValueError:
        return False
    return datetime.now(timezone.utc) >= expiry


def build_lock_record(resource: str, owner: str, expires_at: str) -> dict:
    return {
        "resource": resource,
        "owner": owner,
        "created_at": utc_now_iso(),
        "expires_at": expires_at,
    }


def acquire_write_lock(
    repo_path: str,
    resource: str,
    owner: str,
    ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
) -> tuple[bool, dict | None]:
    existing = read_lock(repo_path, resource)
    if existing:
        if is_lock_expired(existing):
            release_lock(repo_path, resource)
        else:
            return False, existing

    payload = build_lock_record(resource=resource, owner=owner, expires_at=compute_expiry(ttl_seconds))
    write_lock(repo_path, payload)
    return True, payload
