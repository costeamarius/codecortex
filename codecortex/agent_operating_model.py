"""Agent operating model helpers for Codecortex-enabled repositories.

This module defines the minimal v1 rules for participating agents across
IDE, OpenClaw, and other supported environments.
"""

from __future__ import annotations

from typing import Any, Dict, List


PARTICIPATING_AGENT_ENVIRONMENTS = {
    "openclaw",
    "cursor",
    "ide",
    "local_cli",
    "external_agent",
}


def is_participating_agent(environment: str | None) -> bool:
    if environment is None:
        return False
    return environment in PARTICIPATING_AGENT_ENVIRONMENTS


def required_codecortex_operations() -> List[str]:
    return [
        "repository retrieval via CodeCortex CLI when available",
        "supported mutations via the runtime gateway `cortex action`",
        "structured JSON requests via `cortex action --stdin` or `cortex action --request-file`",
    ]


def direct_bypass_examples() -> List[str]:
    return [
        "editing repository files directly when a supported CodeCortex execution path exists",
        "running supported repository operations outside the repo-local CodeCortex CLI",
        "ignoring Codecortex-enabled repo detection and using environment-specific behavior instead",
    ]


def get_agent_operating_model(environment: str | None = None) -> Dict[str, Any]:
    participating = is_participating_agent(environment)
    return {
        "environment": environment,
        "participating_agent": participating,
        "repo_defined_behavior_required": participating,
        "required_operations": required_codecortex_operations() if participating else [],
        "bypass_examples": direct_bypass_examples() if participating else [],
        "parity_expectation": {
            "ide_and_openclaw_should_match": True,
            "shared_interface": "repo-local CodeCortex CLI",
        },
    }
