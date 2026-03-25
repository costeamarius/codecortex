"""OpenClaw alignment helpers for Codecortex-enabled repositories.

This module does not embed OpenClaw logic inside Codecortex.
Instead, it exposes repo-local detection and integration metadata that an
OpenClaw wrapper can use to adopt the repository-defined operating model.
"""

from __future__ import annotations

import os
import warnings
from typing import Any, Dict

from codecortex.integration.openclaw_adapter import OpenClawRuntimeAdapter
from codecortex.memory.detection import detect_repo_binding
from codecortex.runtime.capabilities import build_capabilities_snapshot


def get_openclaw_runtime_detection(repo_path: str) -> Dict[str, Any]:
    binding = detect_repo_binding(repo_path)
    payload = binding.to_dict()
    payload["markers"]["pyproject"] = os.path.isfile(
        os.path.join(binding.repo_root, "pyproject.toml")
    )
    return payload


def get_openclaw_runtime_metadata(repo_path: str) -> Dict[str, Any]:
    detection = get_openclaw_runtime_detection(repo_path)
    capabilities = build_capabilities_snapshot(repo_path)
    runtime = capabilities.get("runtime") or {}
    adapter = OpenClawRuntimeAdapter()
    return {
        **detection,
        "runtime": runtime,
        "openclaw": {
            "role": "runner",
            "must_use_repo_local_cli": True,
            "must_not_embed_execution_logic": True,
            "must_follow_repo_defined_behavior": detection["codecortex_enabled"],
            "bootstrap_if_missing": True,
            "runtime_ready": bool(runtime.get("readiness", {}).get("runtime_actions_available")),
            "graph_context_available": bool(runtime.get("readiness", {}).get("graph_context_available")),
            "warnings": list(runtime.get("warnings") or []),
            "detection": {
                "capabilities_command": "cortex capabilities --path <repo>",
                "readiness_source": "runtime.capabilities",
            },
            "invocation": {
                "canonical_runtime_ingress": runtime.get("ingress") or {},
                "transport": adapter.describe_transport(),
                "supported_actions": list(runtime.get("supported_actions") or []),
            },
        },
    }


def get_openclaw_runtime_bootstrap_plan() -> Dict[str, Any]:
    return {
        "summary": "Install or initialize repo-local Codecortex, then use the repo-local CLI.",
        "steps": [
            "detect Codecortex markers in the target repo",
            "if missing, bootstrap Codecortex into the repository",
            "run `cortex capabilities --path <repo>`",
            "switch to Codecortex-aware mode when enabled",
            "use `cortex action` as the runtime ingress for supported operations",
        ],
    }


def detect_codecortex_enabled(repo_path: str) -> Dict[str, Any]:
    warnings.warn(
        "detect_codecortex_enabled() is deprecated. Use get_openclaw_runtime_detection() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_openclaw_runtime_detection(repo_path)


def get_openclaw_integration_payload(repo_path: str) -> Dict[str, Any]:
    warnings.warn(
        "get_openclaw_integration_payload() is deprecated. Use get_openclaw_runtime_metadata() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_openclaw_runtime_metadata(repo_path)


def get_openclaw_bootstrap_steps() -> Dict[str, Any]:
    warnings.warn(
        "get_openclaw_bootstrap_steps() is deprecated. Use get_openclaw_runtime_bootstrap_plan() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_openclaw_runtime_bootstrap_plan()
