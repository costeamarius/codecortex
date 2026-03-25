# CodeCortex Architecture

CodeCortex is a repository memory system for AI agents, extended with a deterministic execution substrate to enable reliable operation in multi-agent and OpenClaw-aligned environments.

## Architecture Summary

CodeCortex has two primary layers:

1. **Repository memory layer**
   - understands repository structure and semantic relationships
   - persists reusable repository knowledge under `.codecortex/`
   - provides compact retrieval interfaces for AI agents

2. **Deterministic execution layer**
   - provides a repo-local runtime path for controlled file and command execution
   - returns machine-readable results
   - supports validation, logging, and minimal locking in v1

## Core Principle

Repository behavior is **repo-defined**, not **environment-defined**.

If a repository is Codecortex-enabled, participating agents should adopt the same repo-local operating model whether they run in:
- OpenClaw
- an IDE such as Cursor
- another supported external agent environment

## High-Level View

```text
[ IDE Agent ]      [ OpenClaw Agent ]      [ External Agent ]
       \                |                /
        \               |               /
         -> repo-local CodeCortex CLI / runtime ingress <-
                    |
        ------------------------------
        |                            |
  repository memory           execution substrate
        |                            |
   .codecortex/                 repository mutations
```

## Main Components

### 1. Repository Memory

The repository-memory layer includes:
- repository scanning
- symbol graph generation
- semantic framework-specific extraction
- semantic assertion persistence
- feature-oriented graph slices
- compact retrieval commands

Relevant modules include:
- `codecortex/scanner.py`
- `codecortex/graph_builder.py`
- `codecortex/graph_query.py`
- `codecortex/graph_context.py`
- `codecortex/graph_status.py`
- `codecortex/django_semantics.py`
- `codecortex/semantics_store.py`
- `codecortex/feature_graph.py`
- `codecortex/project_context.py`

### 2. Execution Substrate

The repo-local execution substrate includes:
- structured action execution
- safe file editing
- validation-before-commit
- append-only operation logging
- minimal write locking
- structured command execution

Relevant modules include:
- `codecortex/runtime/gateway.py`
- `codecortex/runtime/kernel.py`
- `codecortex/runtime/context_builder.py`
- `codecortex/runtime/policy_engine.py`
- `codecortex/runtime/memory_feedback.py`
- `codecortex/runtime/execution_bridge.py`
- `codecortex/execution/executor.py`
- `codecortex/execution/file_ops.py`
- `codecortex/execution/validators.py`
- `codecortex/execution/logger.py`
- `codecortex/execution/locks.py`
- `codecortex/execution/command_ops.py`
- `codecortex/execution/models.py`
- `codecortex/execution/errors.py`

### 3. OpenClaw and Agent Alignment

Agent-alignment and integration support includes:
- OpenClaw-alignment helpers
- participating-agent operating-model helpers
- repo-local capability exposure

Relevant modules include:
- `codecortex/openclaw_integration.py`
- `codecortex/agent_operating_model.py`
- `cli/cortex_cli.py`

## Repo-Local Runtime Data

CodeCortex persists repository-local runtime data under `.codecortex/`.

Current artifacts include:
- `graph.json`
- `meta.json`
- `features.json`
- `semantics.json`
- `semantics.journal.jsonl`
- `constraints.json`
- `decisions.jsonl`
- `logs/`
- `locks/`
- `state.json`

## Execution Flow (v1)

### Safe file edit flow

```text
Agent decides change
    ↓
repo-local runtime ingress (`cortex action`)
    ↓
runtime gateway + kernel
    ↓
context + policy
    ↓
execution bridge
    ↓
path resolution
    ↓
write lock acquire
    ↓
validation
    ↓
backup
    ↓
atomic replace
    ↓
logging
    ↓
structured result
```

### Safe command flow

```text
Agent requests command
    ↓
repo-local runtime ingress (`cortex action`)
    ↓
runtime gateway + kernel
    ↓
context + policy
    ↓
execution bridge
    ↓
repo-context subprocess execution
    ↓
stdout/stderr capture
    ↓
logging
    ↓
structured result
```

## v1 Execution Semantics

### Validation

v1 validators include:
- JSON parse validation
- Python compile validation
- pass-through behavior for file types without a registered validator

### Logging

Operation logs are append-only JSON lines stored under:

```text
.codecortex/logs/operations.jsonl
```

### Locking

v1 locking behavior:
- write locks only
- one writer per file resource
- lock files stored under `.codecortex/locks/`
- owner recorded in lock payload
- TTL-based expiration
- expired locks may be replaced on the next acquire attempt
- no heartbeat in v1
- no read locks in v1

## CLI Surface

### Memory-oriented commands
- `init`
- `init-agent`
- `scan`
- `update`
- `status`
- `query`
- `context`
- `symbol`
- `impact`
- `remember`
- `feature ...`
- `semantics ...`
- `benchmark ...`

### Execution-oriented commands
- `capabilities`
- `action`

Legacy compatibility commands still exist for `edit-file` and `run-command`, but they route into the same runtime boundary and are not the canonical public interface for participating agents.

## OpenClaw Alignment

OpenClaw is treated as a runner and integration environment.

OpenClaw should:
- detect Codecortex-enabled repositories using the canonical repo rule
- query repo-local capabilities
- use `cortex action` for supported operations
- consume structured results

OpenClaw should not:
- embed file mutation logic
- embed validation logic
- embed locking logic
- redefine repository behavior outside the repo-local operating model

## IDE and External Agent Alignment

Participating agents should:
- use CodeCortex retrieval when available
- use the same repo-local runtime contract for supported operations
- avoid bypassing the execution substrate for supported mutations
- respect the same repo-defined operating rules as OpenClaw

## v1 Scope Boundary

v1 intentionally includes:
- repository memory
- deterministic file editing
- deterministic command execution
- validation
- logging
- minimal write locking
- OpenClaw-aware integration direction

v1 intentionally does not include:
- heartbeat-based lock renewal
- read/write lock separation
- multi-resource transactions
- deadlock handling
- rollback orchestration
- universal enforcement across arbitrary unintegrated tools

## Goal

The architecture is designed to let AI agents understand a repository, retain reusable knowledge across sessions, and operate through a single reliable execution path that remains compatible with OpenClaw and future multi-agent workflows.
