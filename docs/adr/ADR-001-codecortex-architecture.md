# ADR-001: Choose repo-local Codecortex architecture with agent-aware execution coordination

- **Status:** Accepted
- **Date:** 2026-03-22

## Context

The previous direction created low confidence in system reliability.

Problems observed:
- architecture became too distributed and hard to reason about
- responsibility boundaries between AI, Codecortex, and execution were unclear
- global installation and global state increased setup/debug complexity
- OpenClaw risked becoming a place for implementation logic instead of remaining a thin execution wrapper
- reliability suffered because the execution path was not strict enough
- concurrent access by multiple AI agents to the same repository resources was not controlled

The system needs a design where:
- AI makes decisions
- Codecortex provides repository-specific context
- file and command execution happen through a deterministic execution layer
- multiple agents can safely operate on the same repository
- OpenClaw and IDE agents can use the same contract
- the implementation is easy to debug, easy to evolve, and safe to operate

Two approaches were considered:

1. **Global Codecortex engine + global execution layer**
2. **Repo-local Codecortex + repo-local execution layer, with OpenClaw as wrapper/runner**

## Decision

We choose **Approach 2: repo-local Codecortex + repo-local execution layer** as the default architecture for the next version.

In addition, the execution layer is not just a safe file/command wrapper. It is a **coordination layer** for multi-agent access to repository resources.

### Decision summary

Each repository is the unit of isolation and the source of truth.

Codecortex, execution code, configuration, and project-local runtime data live in the repository.
OpenClaw does not contain business logic. It only detects whether Codecortex exists in the repo, optionally bootstraps it, and runs the repo-local CLI.

The execution layer is responsible for:
- safe file and command execution
- validation and logging
- agent-aware locking
- lease/TTL-based resource control
- stale lock recovery
- state protection and rollback behavior

## Primary design goal

The main reason for introducing the execution layer is **multi-agent coordination over shared repository resources**.

The goal is to prevent situations where multiple AI agents:
- read and write the same file concurrently
- overwrite each other’s work
- operate on stale assumptions
- leave resources locked while becoming unresponsive
- produce non-deterministic repository state

In short:

> The execution layer exists to coordinate concurrent AI-agent access to repository resources so reads and writes remain correct, predictable, and recoverable.

## Recommended architecture

### Repository layout

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
      state.py
      backup.py
      errors.py
      models.py
    cli.py
  docs/
    adr/
  tests/
  .codecortex/
    config.json
    logs/
    graph.db
    locks/
    state/
    backups/
```

## OpenClaw responsibility

OpenClaw should act only as a thin wrapper:
- detect if the repo contains Codecortex
- if missing, bootstrap/init it
- invoke the repo-local CLI
- return structured results

OpenClaw must **not** implement:
- domain logic
- file mutation logic
- execution policy
- locking logic
- concurrency management

## Execution rules

### Rule 1: AI must not write directly to disk

All writes must go through the execution layer.

### Rule 2: all agents must use the same execution path

The coordination guarantees only work if every participating agent uses the execution layer.

If one agent edits files directly while another uses the execution layer, consistency guarantees are broken.

### Rule 3: no infinite locks

Locks must never be permanent.
All locks must be lease-based, renewable, and expirable.

## Interface rule

AI should send structured actions, not free-form execution instructions.

Example input:

```json
{
  "action": "edit_file",
  "repo": "/projects/repoA",
  "file": "config.json",
  "changes": [
    {
      "type": "replace",
      "target": "timeout",
      "value": 30
    }
  ]
}
```

Example output:

```json
{
  "status": "success",
  "diff": "...",
  "validation": "passed"
}
```

Blocked example:

```json
{
  "status": "blocked",
  "resource": "config.json",
  "lock_type": "write",
  "owner": "cursor-agent-2",
  "retry_after_seconds": 20
}
```

## Execution layer requirements

The execution layer must provide deterministic operations such as:
- `edit_file_safe(...)`
- `run_command_safe(...)`
- `validate(...)`
- lock acquire / renew / release
- stale lock detection
- backup / restore
- operation logging

Expected properties:
- path resolution inside repo boundaries
- existence checks
- backup before mutation
- validation before commit
- atomic writes
- operation logging
- owner-aware lock tracking
- failure-aware cleanup

## Agent-aware locking model

The execution layer should be **agent-aware**, **time-aware**, and **failure-aware**.

A lock is not only about a file being busy. It should also record:
- the resource
- lock type (`read` or `write`)
- owner agent identity
- operation id
- acquired time
- lease expiration time
- last heartbeat time
- current status

Example lock record:

```json
{
  "resource": "repo://project/config.json",
  "lock_type": "write",
  "owner": "openclaw-agent-1",
  "operation_id": "op_123",
  "status": "active",
  "acquired_at": "2026-03-22T21:55:00Z",
  "lease_expires_at": "2026-03-22T21:55:30Z",
  "last_heartbeat_at": "2026-03-22T21:55:20Z"
}
```

### Locking semantics

Recommended v1 semantics:
- multiple readers allowed
- single writer only
- no readers during active write lock
- writes require exclusive access

### Lease / TTL model

Locks must be lease-based.

Recommended flow:
1. agent acquires lock with TTL
2. agent renews lock periodically while active
3. if agent becomes unresponsive and stops renewing
4. lock expires automatically
5. execution layer marks operation stale/abandoned
6. recovery/cleanup runs if needed
7. resource becomes available again

### Why estimated completion time is not enough

Estimated completion time is useful as a retry hint, but not as a safety mechanism.

An agent may:
- hang
- crash
- lose connectivity
- stall in a loop
- stop heartbeating

Because of this, the system must rely on:
- lease expiration
- heartbeat/renew
- stale lock detection

not on estimated duration alone.

### Retry model

For v1, blocked agents should use a simple polling model:
- execution layer returns `blocked`
- response includes `retry_after_seconds`
- the waiting agent retries later

Event-based notification can be added later if needed.

## Failure recovery and state protection

The execution layer must protect repository state against failed operations.

### Single-file operations

For file mutation, the recommended safe pattern is:
1. acquire write lock
2. read current state
3. create backup or snapshot
4. prepare new content
5. validate new content
6. write to temp file
7. atomically replace original
8. log success
9. release lock

If failure occurs before atomic replacement, the original file remains unchanged.

### Multi-step operations

For operations affecting multiple resources, the execution layer should track:
- operation scope
- resource list
- backups per resource
- current step
- rollback eligibility

If a later step fails, the layer should either:
- rollback previous changes
- or mark the result as partial failure with explicit recovery metadata

The exact rollback policy can evolve, but recovery hooks must exist from the beginning.

### Stale operation recovery

If an agent dies while holding a lock:
- the lease expires
- the operation is marked stale
- incomplete state is inspected
- backup/rollback or cleanup runs if necessary
- the lock is released

## Recommended execution modules

### `executor.py`
Coordinates the full operation flow:
- schema validation
- lock acquisition
- file/command execution
- validation
- logging
- cleanup and release in `finally`

### `file_ops.py`
Responsible for:
- repo-bounded path resolution
- file reads
- backup creation
- temp file handling
- atomic writes
- diff generation

### `validators.py`
Responsible for:
- JSON validation
- Python compile validation
- YAML/TOML validation
- optional linting hooks

### `logger.py`
Responsible for structured operation logging.

### `locks.py`
Responsible for:
- acquire read lock
- acquire write lock
- renew lock
- release lock
- detect stale locks

### `state.py`
Tracks:
- active operations
- resource versions / hashes
- operation metadata
- lock metadata references

### `backup.py`
Responsible for:
- snapshot creation
- restore
- cleanup of old backups

### `models.py`
Defines structured contracts:
- action models
- result models
- lock models
- operation models

### `errors.py`
Defines explicit execution and coordination errors.

## CLI rule

The CLI is the single operational entrypoint.

Examples:

```bash
cd /path/to/repo && python -m codecortex.cli edit-file ...
```

or, if installed:

```bash
cd /path/to/repo && codecortex-exec edit-file ...
```

All supported agents should go through this interface.

## Why this decision

This approach is preferred because it optimizes for current needs:
- simpler setup
- easier debugging
- better isolation between repositories
- less hidden global state
- cleaner Git workflow
- lower architectural risk
- easier enforcement of a single execution path
- better multi-agent coordination within a repo

This also matches the operational reality:
- OpenClaw should go to the repo
- not the other way around

In short:

> Do not bring Codecortex into OpenClaw as global logic.  
> Bring OpenClaw to the repo and let it run the repo-local Codecortex.

## Rejected alternative

### Alternative: global Codecortex engine + global execution layer

This remains conceptually interesting for future platform-scale orchestration, but is rejected for now.

Reasons:
- higher complexity too early
- harder bootstrap and lifecycle management
- more difficult debugging
- greater risk of duplicated responsibility
- more fragile shared/global state
- weaker local isolation

This option may be revisited later only if there is a proven need for:
- strong multi-repo orchestration
- shared cross-repo intelligence
- centralized execution governance

## Consequences

### Positive

- each repo is self-contained
- no dependency on hidden global runtime state
- easier to load in Cursor and other IDEs
- easier testing and reproducibility
- OpenClaw skills stay simple and reliable
- failure domains are smaller
- architecture is easier to explain and maintain
- concurrency behavior becomes explicit instead of accidental

### Negative

- code may be repeated across repositories unless extracted carefully later
- upgrades across many repos may require migration tooling
- shared engine features are less centralized
- scaling across many repos is less elegant than a mature global platform
- locking and recovery design add implementation complexity

## Rules to enforce

### Must do

- keep Codecortex implementation inside the repo
- keep execution logic inside the repo
- use a single CLI entrypoint for operational actions
- keep OpenClaw skills thin
- use structured contracts between AI and execution layer
- store repo-local runtime data in `.codecortex/`
- log execution events
- use lease-based locks
- support stale lock recovery
- protect writes with backup + atomic commit behavior

### Must not do

- do not put business logic in OpenClaw skills
- do not let AI write files directly
- do not create a second execution layer in OpenClaw
- do not introduce global Codecortex state by default
- do not allow permanent locks
- do not bypass the execution layer for participating agents

## Initial detection and enforcement policy

Recommended policy:

1. If repo contains Codecortex, use it.
2. If repo does not contain Codecortex, bootstrap/init it.
3. All project modifications must go through the repo-local execution layer.
4. Any multi-agent participant must use the same lock-aware execution interface.

Detection examples:
- `test -d codecortex`
- `test -f .codecortex/config.json`

## Follow-up work

1. Define the first stable CLI contract.
2. Implement repo-local execution primitives.
3. Implement lock lease model (`acquire`, `renew`, `release`, `expire`).
4. Add stale lock recovery.
5. Add validation and logging.
6. Add backup and restore behavior.
7. Add bootstrap/init flow.
8. Add OpenClaw wrapper skills with no embedded logic.
9. Add tests around edit, validation, command execution, lock conflicts, stale lock handling, and recovery behavior.

## Final statement

Codecortex understands the system.  
Execution Layer controls and coordinates the system.  
AI decides over the system.
