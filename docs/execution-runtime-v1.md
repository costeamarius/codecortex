# Execution Runtime v1

- **Status:** Accepted for implementation
- **Date:** 2026-03-22

## Purpose

This document defines the initial runtime behavior for the minimal execution layer introduced in ADR-002.

## Runtime directories

Execution-related runtime data lives under `.codecortex/`.

### Logs

Location:

```text
.codecortex/logs/
```

v1 behavior:
- append-only operation logs
- machine-readable JSON lines format
- stores both success and failure events

### Locks

Location:

```text
.codecortex/locks/
```

v1 behavior:
- one write lock per file resource
- lock stored as local JSON file
- owner recorded in lock payload
- TTL-based expiration metadata
- expired locks may be replaced on the next acquire attempt
- no heartbeat in v1
- no read locks in v1

### State

Location:

```text
.codecortex/state.json
```

v1 behavior:
- reserved for lightweight execution metadata
- may track runtime version or minimal execution state
- intentionally simple in v1

### Backups

v1 strategy:
- simple adjacent backup using `<target>.bak`
- no centralized backup orchestration yet
- backup retained for manual recovery if needed

## Detection note

For v1, `.codecortex/` and repo-local CodeCortex structure are sufficient practical signals for a Codecortex-enabled repository.
