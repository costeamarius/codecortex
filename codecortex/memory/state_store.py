"""Repo-local state directory helpers."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional


REQUIRED_META_FIELDS = ("schema_version", "repo_id", "initialized_at")
REQUIRED_RUNTIME_STATE_FIELDS = (
    "repo_initialized",
    "graph_dirty",
    "last_action_at",
    "last_action_id",
    "last_scan_at",
    "last_scan_commit",
)


def get_state_dir(repo_root: str) -> str:
    return os.path.join(repo_root, ".codecortex")


def get_meta_path(repo_root: str) -> str:
    return os.path.join(get_state_dir(repo_root), "meta.json")


def build_state_paths(repo_root: str) -> Dict[str, str]:
    state_dir = get_state_dir(repo_root)
    return {
        "dir": state_dir,
        "meta": os.path.join(state_dir, "meta.json"),
        "state": os.path.join(state_dir, "state.json"),
        "graph": os.path.join(state_dir, "graph.json"),
        "features": os.path.join(state_dir, "features.json"),
        "semantics": os.path.join(state_dir, "semantics.json"),
        "semantics_journal": os.path.join(state_dir, "semantics.journal.jsonl"),
        "constraints": os.path.join(state_dir, "constraints.json"),
        "decisions": os.path.join(state_dir, "decisions.jsonl"),
    }


def read_json_file(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def is_valid_meta(payload: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(payload, dict):
        return False

    for field in REQUIRED_META_FIELDS:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            return False

    return True


def load_valid_meta(repo_root: str) -> Optional[Dict[str, Any]]:
    payload = read_json_file(get_meta_path(repo_root))
    if not is_valid_meta(payload):
        return None
    return payload


def build_initial_runtime_state() -> Dict[str, Any]:
    return {
        "repo_initialized": True,
        "graph_dirty": False,
        "last_action_at": None,
        "last_action_id": None,
        "last_scan_at": None,
        "last_scan_commit": None,
    }


def is_valid_runtime_state(payload: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(payload, dict):
        return False

    return all(field in payload for field in REQUIRED_RUNTIME_STATE_FIELDS)
