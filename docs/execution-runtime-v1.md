# Execution Runtime v1

- **Status:** Accepted for implementation
- **Date:** 2026-03-22

## Purpose

This document defines the initial runtime behavior for the minimal execution layer introduced in ADR-002.

The canonical participating-agent ingress is `cortex action`, which routes through:

`Agent -> AgentGateway -> RuntimeKernel -> Policy -> ExecutionBridge -> MemoryFeedback`

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
- lightweight runtime execution metadata
- tracks repo initialization and graph freshness state
- tracks the last action timestamp and action id
- tracks the last graph scan timestamp and commit

### Backups

v1 strategy:
- simple adjacent backup using `<target>.bak`
- no centralized backup orchestration yet
- backup retained for manual recovery if needed

## Detection note

For v1, a repository is CodeCortex-enabled only when `.codecortex/meta.json` exists and is valid.

`.codecortex/`, `AGENTS.md`, and other markers are advisory only and do not by themselves authorize runtime actions.
