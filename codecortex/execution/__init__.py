"""Internal execution substrate for deterministic repository operations.

The public runtime boundary lives under ``codecortex.runtime``. This package
contains repo-local execution primitives used by the runtime kernel.
"""

from .models import ExecutionAction, ExecutionResult, ValidationResult

__all__ = [
    "ExecutionAction",
    "ExecutionResult",
    "ValidationResult",
]
