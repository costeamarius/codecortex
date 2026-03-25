"""Canonical repo binding models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class RepoBinding:
    repo_root: str
    state_dir: str
    meta_path: str
    enabled: bool
    meta: Optional[Dict[str, Any]]
    markers: Dict[str, bool]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo": self.repo_root,
            "state_dir": self.state_dir,
            "meta_path": self.meta_path,
            "codecortex_enabled": self.enabled,
            "meta": self.meta,
            "markers": self.markers,
        }
