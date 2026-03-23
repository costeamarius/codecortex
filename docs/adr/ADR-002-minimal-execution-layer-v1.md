# ADR-002: Repo-local Codecortex with minimal execution layer (v1), extensible to coordinated multi-agent system

- **Status:** Accepted
- **Date:** 2026-03-22

## Context

Previous iterations introduced excessive architectural complexity too early, reducing confidence in system behavior and making debugging difficult.

Observed issues:

- unclear separation between reasoning (AI) and execution
- premature introduction of global state and coordination mechanisms
- OpenClaw taking on implementation responsibilities instead of acting as a runner
- lack of deterministic execution guarantees
- difficulty validating system behavior end-to-end

At the same time, the system must evolve toward:

- safe execution of file and command operations
- consistent behavior across IDE and OpenClaw agents
- future support for multi-agent coordination
- clear and debuggable execution flow

## Decision

We adopt a repo-local Codecortex architecture with a minimal deterministic execution layer (v1).

The system will:

- keep all logic inside the repository
- use OpenClaw strictly as a thin wrapper
- enforce a single execution path via a CLI
- implement only the minimum coordination features required for correctness
- defer advanced coordination (multi-agent locking, rollback orchestration) to later versions

## Core Principles

### 1. Repository is the unit of isolation

Each repository contains:

- Codecortex implementation
- execution layer
- runtime data

There is no global Codecortex state in v1.

### 2. Single execution path

All operations must go through a single entrypoint:

```bash
cd /repo && python -m codecortex.cli <action>
```

No agent is allowed to:

- write files directly
- bypass the execution layer

### 3. Separation of concerns

- AI agent → decides what to do
- Codecortex → provides repository context
- Execution layer → performs actions safely

### 4. OpenClaw is a runner, not a logic container

OpenClaw responsibilities:

- detect Codecortex presence
- bootstrap if missing
- call the repo-local CLI
- return results

OpenClaw must NOT:

- implement execution logic
- perform file mutations
- manage locks or coordination

## Repository Structure

```text
repo/
 codecortex/
   core/
   execution/
     executor.py
     file_ops.py
     validators.py
     logger.py
     locks.py
   cli.py
 .codecortex/
   logs/
   state.json
```

## Execution Layer (v1 scope)

The execution layer provides deterministic operations:

### Required functions

- `edit_file_safe(...)`
- `run_command_safe(...)`
- `validate(...)`
- `log_operation(...)`

### Safe file write pattern

- resolve path inside repo
- check file existence
- create backup (simple copy)
- apply change in memory
- validate result
- write to temp file
- atomic replace
- log result

## Validation (v1)

- JSON validation (if applicable)
- Python compile check (if applicable)
- optional lightweight checks

## Minimal Locking (v1)

Locking is intentionally simplified.

### Rules

- only write locks
- one writer per file
- lock stored locally in `.codecortex/locks/`

### Lock structure (v1)

```json
{
  "resource": "config.json",
  "owner": "agent_id",
  "created_at": "...",
  "expires_at": "..."
}
```

### Behavior

- acquire lock before write
- if locked → return blocked
- lock expires automatically after TTL
- no heartbeat in v1

## Non-goals (v1)

- no read/write lock separation
- no multi-resource transactions
- no complex deadlock handling

## CLI Contract

### Input (structured)

```json
{
  "action": "edit_file",
  "file": "config.json",
  "changes": [...]
}
```

### Output

```json
{
  "status": "success",
  "diff": "...",
  "validation": "passed"
}
```

or:

```json
{
  "status": "blocked",
  "retry_after_seconds": 10
}
```

## OpenClaw Integration

### Required behavior

Detect Codecortex:

```bash
test -d codecortex
```

If missing → bootstrap:

```bash
git clone <codecortex-template> codecortex
```

Execute:

```bash
cd /repo && python -m codecortex.cli ...
```

## Enforcement Policy

System-level enforcement replaces reliance on AI memory.

Rules:

- If Codecortex exists → must be used
- If missing → must be installed
- All modifications go through CLI
- No direct file edits allowed for participating agents

## Logging (v1)

All operations must be logged:

```json
{
  "timestamp": "...",
  "action": "edit_file",
  "file": "...",
  "status": "success"
}
```

Stored in:

```text
.codecortex/logs/
```

## Failure Handling (v1)

- if validation fails → do not write
- if write fails → original file remains
- backup is kept for manual recovery
- no automatic rollback orchestration

## Why this approach

This design is chosen because it:

- minimizes initial complexity
- enforces a deterministic execution path
- avoids global state and hidden coupling
- keeps debugging simple
- aligns with OpenClaw’s role as executor
- allows gradual evolution toward multi-agent coordination

## Consequences

### Positive

- predictable behavior
- easy debugging
- clear ownership of logic
- consistent execution across environments
- safe file operations

### Negative

- limited concurrency support
- duplicated logic across repos
- manual upgrades between versions
- limited coordination between agents

## Future Evolution (IMPORTANT)

### v2 — improved coordination

- add heartbeat-based locks
- introduce read/write lock separation
- improve stale lock detection
- add retry strategies

### v3 — advanced coordination

- multi-resource operations
- rollback strategies
- operation state tracking
- conflict detection

### v4 — optional global layer

- shared Codecortex engine
- cross-repo knowledge
- centralized execution governance

## Explicit Non-Goals (v1)

- global execution layer
- distributed coordination system
- complex transaction management
- full consistency guarantees under arbitrary conditions

## Final Statement

Codecortex provides context.  
Execution Layer enforces correctness.  
AI proposes actions.  
The system controls execution.

This version prioritizes clarity, determinism, and implementation feasibility over completeness.
