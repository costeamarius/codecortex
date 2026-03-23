"""Execution layer for deterministic repository operations.

This package hosts the repo-local execution substrate introduced in ADR-002.
It is intentionally minimal in v1 and will evolve in later phases.
"""

from .executor import execute_action
from .models import ExecutionAction, ExecutionResult, LockRecord, ValidationResult

__all__ = [
    "execute_action",
    "ExecutionAction",
    "ExecutionResult",
    "LockRecord",
    "ValidationResult",
]
