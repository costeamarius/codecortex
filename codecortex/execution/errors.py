"""Execution-layer error types."""


class ExecutionError(Exception):
    """Base execution-layer error."""


class PathViolationError(ExecutionError):
    """Raised when a path escapes repository boundaries."""


class ValidationError(ExecutionError):
    """Raised when validation fails before commit."""


class LockConflictError(ExecutionError):
    """Raised when a resource is currently locked for mutation."""


class CommandExecutionError(ExecutionError):
    """Raised when a command execution fails."""


class RuntimeBypassError(ExecutionError):
    """Raised when execution is invoked outside the runtime-controlled path."""
