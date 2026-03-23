# Phase 3 Contract Decisions

- **Status:** Accepted for implementation
- **Date:** 2026-03-22

## Summary

Phase 3 fixes the minimal execution contracts for v1.

### Actions
- `edit_file`
- `run_command`

### Planned CLI commands
- `edit-file`
- `run-command`

### Result statuses
- `success`
- `failure`
- `blocked`
- `not_implemented`

### Contract rules
- actions are structured, not free-form
- action payloads are repo-local and machine-readable
- failures are structured
- lock conflicts return `blocked`
- unsupported or not-yet-implemented actions may return `not_implemented`
- CLI remains the canonical interface for participating agents

### Operating contract discovery in v1
Agents discover the operating model through:
- repo-local CodeCortex presence
- repo-local CLI
- repository instructions
- project documentation
