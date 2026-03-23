# Phase 9 CLI Integration

- **Status:** Implemented
- **Date:** 2026-03-22

## Implemented in this phase

- CLI command for safe file editing: `edit-file`
- CLI command for safe command execution: `run-command`
- machine-readable JSON output for execution commands
- coexisting memory-oriented and execution-oriented CLI surfaces
- `capabilities` command for basic operating-mode exposure

## v1 notes

- the existing memory CLI remains intact
- execution commands use the same repo-local execution layer as internal code paths
- `capabilities` provides a first minimal machine-readable exposure of the repo operating model
