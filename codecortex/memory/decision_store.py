"""Helpers for append-only decision memory under .codecortex/."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from codecortex.semantics_store import append_jsonl, read_jsonl


def append_decision(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    entry = normalize_decision(payload)
    append_jsonl(path, entry)
    return entry


def list_decisions(path: str, limit: int | None = None) -> List[Dict[str, Any]]:
    decisions = [normalize_decision(entry) for entry in read_jsonl(path) if isinstance(entry, dict)]
    if limit is None:
        return decisions
    return decisions[-limit:]


def query_decisions(path: str, targets: Set[str], limit: int = 10) -> List[Dict[str, Any]]:
    if not targets:
        return []

    matched = []
    for decision in list_decisions(path):
        if _collect_strings(decision) & targets:
            matched.append(decision)
    return matched[-limit:]


def normalize_decision(payload: Dict[str, Any]) -> Dict[str, Any]:
    entry = dict(payload)
    tags = entry.get("tags")
    if not isinstance(tags, list):
        entry["tags"] = []
    else:
        entry["tags"] = [str(tag) for tag in tags if str(tag).strip()]

    references = entry.get("references")
    if not isinstance(references, list):
        entry["references"] = []
    else:
        entry["references"] = [reference for reference in references if isinstance(reference, str) and reference]

    return entry


def _collect_strings(payload: Any) -> Set[str]:
    values: Set[str] = set()
    _collect_strings_into(payload, values)
    return values


def _collect_strings_into(payload: Any, values: Set[str]) -> None:
    if isinstance(payload, str):
        values.add(payload)
        return
    if isinstance(payload, dict):
        for value in payload.values():
            _collect_strings_into(value, values)
        return
    if isinstance(payload, list):
        for item in payload:
            _collect_strings_into(item, values)
