"""Canonical repository detection and binding."""

from __future__ import annotations

import os
from typing import Dict, Iterable

from codecortex.memory.repo_state import RepoBinding
from codecortex.memory.state_store import get_meta_path, get_state_dir, load_valid_meta


def _normalize_start_path(path: str) -> str:
    absolute = os.path.abspath(path)
    if os.path.isdir(absolute):
        return absolute
    return os.path.dirname(absolute)


def _iter_ancestors(path: str) -> Iterable[str]:
    current = path
    while True:
        yield current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent


def _collect_markers(repo_root: str) -> Dict[str, bool]:
    meta = load_valid_meta(repo_root)
    return {
        "codecortex_dir": os.path.isdir(os.path.join(repo_root, "codecortex")),
        "runtime_dir": os.path.isdir(get_state_dir(repo_root)),
        "agents_md": os.path.isfile(os.path.join(repo_root, "AGENTS.md")),
        "meta_json": os.path.isfile(get_meta_path(repo_root)),
        "valid_meta": meta is not None,
    }


def _bind(repo_root: str) -> RepoBinding:
    meta = load_valid_meta(repo_root)
    markers = _collect_markers(repo_root)
    return RepoBinding(
        repo_root=repo_root,
        state_dir=get_state_dir(repo_root),
        meta_path=get_meta_path(repo_root),
        enabled=meta is not None,
        meta=meta,
        markers=markers,
    )


def detect_repo_binding(path: str) -> RepoBinding:
    start_path = _normalize_start_path(path)
    advisory_candidate = None

    for candidate in _iter_ancestors(start_path):
        binding = _bind(candidate)
        if binding.enabled:
            return binding
        if advisory_candidate is None and any(
            (
                binding.markers["codecortex_dir"],
                binding.markers["runtime_dir"],
                binding.markers["agents_md"],
                binding.markers["meta_json"],
            )
        ):
            advisory_candidate = binding

    if advisory_candidate is not None:
        return advisory_candidate
    return _bind(start_path)
