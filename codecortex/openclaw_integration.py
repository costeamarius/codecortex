"""OpenClaw alignment helpers for Codecortex-enabled repositories.

This module does not embed OpenClaw logic inside Codecortex.
Instead, it exposes repo-local detection and integration metadata that an
OpenClaw wrapper can use to adopt the repository-defined operating model.
"""

from __future__ import annotations

import os
from typing import Any, Dict


def detect_codecortex_enabled(repo_path: str) -> Dict[str, Any]:
    repo_path = os.path.abspath(repo_path)
    markers = {
        "codecortex_dir": os.path.isdir(os.path.join(repo_path, "codecortex")),
        "runtime_dir": os.path.isdir(os.path.join(repo_path, ".codecortex")),
        "agents_md": os.path.isfile(os.path.join(repo_path, "AGENTS.md")),
        "pyproject": os.path.isfile(os.path.join(repo_path, "pyproject.toml")),
    }
    enabled = markers["codecortex_dir"] or markers["runtime_dir"]
    return {
        "codecortex_enabled": enabled,
        "repo": repo_path,
        "markers": markers,
    }


def get_openclaw_integration_payload(repo_path: str) -> Dict[str, Any]:
    detection = detect_codecortex_enabled(repo_path)
    return {
        **detection,
        "openclaw": {
            "role": "runner",
            "must_use_repo_local_cli": True,
            "must_not_embed_execution_logic": True,
            "must_follow_repo_defined_behavior": detection["codecortex_enabled"],
            "bootstrap_if_missing": True,
            "expected_commands": {
                "capabilities": "cortex capabilities --path <repo>",
                "edit_file": "cortex edit-file --path <repo> --file <file> --content <content>",
                "run_command": "cortex run-command --path <repo> --command <command>",
            },
        },
    }


def get_openclaw_bootstrap_steps() -> Dict[str, Any]:
    return {
        "summary": "Install or initialize repo-local Codecortex, then use the repo-local CLI.",
        "steps": [
            "detect Codecortex markers in the target repo",
            "if missing, bootstrap Codecortex into the repository",
            "run `cortex capabilities --path <repo>`",
            "switch to Codecortex-aware mode when enabled",
            "use `cortex edit-file` / `cortex run-command` for supported operations",
        ],
    }
