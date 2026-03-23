# Test Matrix v1

- **Status:** Active
- **Date:** 2026-03-23

## Execution layer coverage

| Area | Covered | Notes |
|---|---:|---|
| Path resolution safety | Yes | `test_execution_file_ops.py` |
| Backup creation | Yes | covered via `edit_file_safe(...)` |
| Atomic write behavior | Yes | covered via successful file replacement flow |
| JSON validation | Yes | `test_execution_validators.py` |
| Python validation | Yes | `test_execution_validators.py` |
| Logging output | Yes | `test_execution_logging.py` |
| Lock acquire/release | Yes | `test_execution_locks.py` |
| Expired lock replacement | Yes | `test_execution_locks.py` |
| Command success/failure | Yes | `test_execution_command_ops.py` |

## CLI coverage

| Area | Covered | Notes |
|---|---:|---|
| `edit-file` success | Yes | `test_cli_execution.py` |
| `edit-file` failure | Yes | `test_cli_execution.py` |
| `edit-file` blocked | Yes | `test_cli_execution.py` |
| `run-command` success | Yes | `test_cli_execution.py` |
| `run-command` failure | Yes | `test_cli_execution.py` |
| `capabilities` output | Yes | `test_cli_execution.py` |

## Regression coverage

| Area | Covered | Notes |
|---|---:|---|
| Memory/graph tests still pass | Yes | existing suite retained |
| Execution changes do not break memory behavior | Yes | validated by full suite |
| Basic non-OpenClaw usage still works | Yes | execution helpers and repo-local logic are standalone |
