# Implementation Plan — ADR-001 aligned to ADR-002 and ADR-003

- **Status:** Active
- **Date:** 2026-03-22
- **Purpose:** Execution checklist for implementing the strategic direction from ADR-001 through the minimal, practical scope defined in ADR-002, while aligning participating agents with the repository-defined operating model from ADR-003.

---

## How to use this file

This file is the implementation checklist for the next evolution of CodeCortex.

Rules:
- mark items with `[x]` only when implemented
- keep incomplete work as `[ ]`
- if scope changes, update this file explicitly
- if a step is superseded, annotate it instead of silently removing history
- keep this document aligned with the real product state

---

## Goal

Implement the next version of CodeCortex as:

> a repository memory system for AI agents, extended with a deterministic execution substrate to enable reliable operation in multi-agent and OpenClaw-aligned environments.

This implementation phase must:
- preserve the strategic direction from **ADR-001**
- follow the minimal and feasible execution scope from **ADR-002**
- establish the repository-defined agent operating model from **ADR-003**

---

## Phase 0 — Baseline understanding and documentation alignment

### 0.1 Repository understanding
- [x] Scan current repository structure
- [x] Identify current CLI entrypoints
- [x] Identify current graph/memory components
- [x] Identify current test baseline
- [x] Confirm current project maturity level

### 0.2 Architecture documentation
- [x] Preserve ADR-001 as strategic architecture direction
- [x] Create ADR-002 for minimal execution layer v1
- [x] Create ADR-003 for repository-defined agent operating model
- [x] Update README to reflect the new direction
- [ ] Update `docs/architecture.md` to align with ADR-001, ADR-002, and ADR-003
- [ ] Verify all user-facing docs are in English

---

## Phase 1 — Define implementation boundaries

### 1.1 Preserve existing repository memory capabilities
- [x] Confirm which current modules remain part of v1 without major changes
- [x] Confirm current CLI commands that stay memory-oriented
- [x] Confirm `.codecortex/` storage artifacts that remain valid

### 1.2 Define minimal execution v1 boundary
- [x] Finalize v1 execution scope from ADR-002
- [x] Confirm non-goals for v1 inside implementation docs
- [x] Confirm that advanced coordination remains deferred

### 1.3 Define integration boundary
- [x] Confirm OpenClaw role as wrapper/runner only
- [x] Confirm repo-local CLI as the only execution path
- [x] Confirm participating agents must not mutate files directly
- [x] Confirm that Codecortex remains usable without OpenClaw

### 1.4 Define agent operating model boundary
- [x] Define what qualifies a repository as Codecortex-enabled
- [x] Define the minimal detection markers for v1
- [x] Define what behavior changes when Codecortex mode is active
- [x] Confirm that repository behavior is repo-defined, not environment-defined

---

## Phase 2 — Restructure repository for execution-layer introduction

### 2.1 Target package structure
- [x] Create `codecortex/execution/`
- [x] Add `codecortex/execution/__init__.py`
- [x] Create `codecortex/execution/executor.py`
- [x] Create `codecortex/execution/file_ops.py`
- [x] Create `codecortex/execution/validators.py`
- [x] Create `codecortex/execution/logger.py`
- [x] Create `codecortex/execution/locks.py`
- [x] Create `codecortex/execution/errors.py`
- [x] Create `codecortex/execution/models.py`

### 2.2 Runtime storage preparation
- [x] Define `.codecortex/logs/` behavior
- [x] Define `.codecortex/locks/` behavior
- [x] Define `.codecortex/state.json` behavior
- [x] Define backup location strategy for v1
- [x] Define any repo-level marker/config needed for Codecortex-enabled detection

---

## Phase 3 — Define execution contracts

### 3.1 Action model
- [x] Define structured action schema for `edit_file`
- [x] Define structured action schema for `run_command`
- [x] Define common execution result schema
- [x] Define blocked result schema
- [x] Define validation result schema

### 3.2 Error model
- [x] Define execution-layer error types
- [x] Define validation failure behavior
- [x] Define blocked/lock conflict behavior
- [x] Define safe failure output format

### 3.3 CLI contract
- [x] Define initial CLI command set for execution operations
- [x] Decide command naming (`edit-file`, `run-command`, etc.)
- [x] Define JSON in/out expectations where needed
- [x] Ensure CLI remains repo-local and deterministic
- [x] Define how agents discover the supported operating contract

---

## Phase 4 — Implement safe file operations (v1)

### 4.1 Path safety
- [x] Implement repo-bounded path resolution
- [x] Prevent path escape outside repo root
- [x] Validate target existence rules

### 4.2 Backup and write flow
- [x] Implement simple backup before mutation
- [x] Implement in-memory change application
- [x] Implement temp-file write flow
- [x] Implement atomic replace
- [x] Preserve original file on failure

### 4.3 Edit operation
- [x] Implement `edit_file_safe(...)`
- [x] Return structured success payload
- [x] Return structured failure payload
- [x] Return diff output or diff summary

---

## Phase 5 — Implement validation layer (v1)

### 5.1 Minimal validators
- [x] Implement JSON validation
- [x] Implement Python compile validation
- [x] Implement extension-based validator dispatch
- [x] Define behavior for files with no validator

### 5.2 Validation integration
- [x] Validate before commit
- [x] Block commit on validation failure
- [x] Return validation details in result payload

---

## Phase 6 — Implement logging layer (v1)

### 6.1 Logging schema
- [x] Define operation log schema
- [x] Include timestamp, action, target, status
- [x] Include validation status where applicable
- [x] Include lock-related metadata where applicable
- [x] Include agent/environment metadata where useful

### 6.2 Logging implementation
- [x] Implement append-only operation logging
- [x] Store logs under `.codecortex/logs/`
- [x] Ensure failed operations are also logged

---

## Phase 7 — Implement minimal locking (v1)

### 7.1 Lock model
- [x] Define write-lock structure
- [x] Define TTL field behavior
- [x] Define owner field behavior
- [x] Define lock file naming/storage strategy

### 7.2 Lock operations
- [x] Implement acquire write lock
- [x] Implement release write lock
- [x] Implement expired lock detection during acquire
- [x] Return blocked payload when resource is locked

### 7.3 v1 lock rules
- [x] Enforce one writer per file
- [x] Do not implement heartbeat in v1
- [x] Do not implement read locks in v1
- [x] Document lock limitations clearly

---

## Phase 8 — Implement command execution path (v1)

### 8.1 Command model
- [x] Define minimal `run_command_safe(...)` contract
- [x] Ensure commands execute in repo context
- [x] Define stdout/stderr capture behavior
- [x] Define failure behavior for non-zero exit codes

### 8.2 Safety boundary
- [x] Decide whether command allowlisting is in v1 or deferred
- [x] Document command execution constraints
- [x] Log command execution results

---

## Phase 9 — Integrate execution layer into CLI

### 9.1 New execution commands
- [x] Add CLI command for safe file editing
- [x] Add CLI command for safe command execution
- [x] Ensure output is machine-readable when needed

### 9.2 Maintain current memory CLI
- [x] Keep existing graph/memory CLI commands working
- [x] Avoid breaking current repository-memory functionality
- [x] Ensure execution and memory flows coexist clearly

### 9.3 Codecortex-enabled operating mode exposure
- [x] Add a clear way to detect that a repo is Codecortex-enabled
- [x] Expose enough repo-local information for external agents to adopt the correct workflow
- [x] Ensure the CLI is the canonical interface for participating agents

---

## Phase 10 — OpenClaw alignment

### 10.1 Runner model
- [x] Confirm OpenClaw uses repo-local CLI only
- [x] Confirm OpenClaw does not embed execution logic
- [x] Define expected invocation examples for OpenClaw

### 10.2 Bootstrap model
- [x] Define detection rule for existing Codecortex in repo
- [x] Define bootstrap behavior if missing
- [x] Document OpenClaw integration flow

### 10.3 Codecortex-aware behavior
- [x] Define how OpenClaw detects Codecortex-enabled repositories
- [x] Define how OpenClaw switches into Codecortex mode
- [x] Define expected behavior parity between IDE agents and OpenClaw agents
- [x] Document that OpenClaw must follow repo-defined operating rules when Codecortex is present

---

## Phase 11 — IDE and external agent alignment

### 11.1 IDE alignment
- [x] Define expected IDE-agent workflow for Codecortex-enabled repos
- [x] Ensure IDE workflow uses the same repo-local CLI contract
- [x] Document parity expectations between IDE and OpenClaw

### 11.2 Participating agent rules
- [x] Define what makes an agent a participating agent
- [x] Define which operations must go through Codecortex
- [x] Define which direct behaviors are considered bypasses
- [x] Document how external agents should adopt the repo-defined operating model

---

## Phase 12 — Tests

### 12.1 Unit tests for execution layer
- [x] Add tests for path resolution safety
- [x] Add tests for backup creation
- [x] Add tests for atomic write behavior
- [x] Add tests for JSON validation
- [x] Add tests for Python validation
- [x] Add tests for logging output
- [x] Add tests for lock acquire/release
- [x] Add tests for expired lock replacement

### 12.2 CLI tests
- [x] Add tests for execution CLI commands
- [x] Add tests for blocked responses
- [x] Add tests for failure responses
- [x] Add tests for detection / operating-mode reporting if applicable

### 12.3 Regression tests
- [x] Ensure existing memory/graph tests still pass
- [x] Confirm new work does not break current repository memory behavior
- [x] Confirm basic Codecortex behavior still works without OpenClaw

---

## Phase 13 — Documentation and user-facing alignment

### 13.1 README and architecture docs
- [x] Update README to reflect current product direction
- [x] Update architecture docs with execution-layer structure
- [x] Add v1 execution examples to docs
- [x] Add OpenClaw-aligned workflow examples
- [x] Add Codecortex-enabled repository behavior examples

### 13.2 CLI and examples
- [x] Update CLI help text to match implemented behavior
- [x] Add examples for edit flow
- [x] Add examples for blocked lock flow
- [x] Add examples for validation failure flow
- [x] Add examples for environment-independent usage

### 13.3 Product-state discipline
- [x] Review docs after each implementation milestone
- [x] Keep docs aligned with shipped behavior
- [x] Avoid documenting unimplemented behavior as available

---

## Phase 14 — v1 release readiness

### 14.1 Functional readiness
- [x] Repository memory features still operate correctly
- [x] Minimal execution path works end-to-end
- [x] Validation works for supported file types
- [x] Logging works for all execution actions
- [x] Locking works for single-file write coordination
- [x] Codecortex-enabled repo detection works for supported integrations

### 14.2 Scope discipline
- [x] Confirm heartbeat is not implemented in v1
- [x] Confirm read/write lock separation is deferred
- [x] Confirm rollback orchestration is deferred
- [x] Confirm multi-resource transactions are deferred

### 14.3 Release docs
- [x] Summarize what v1 supports
- [x] Summarize what v1 explicitly does not support
- [x] Summarize how OpenClaw-aligned behavior works in v1
- [x] Prepare next-step notes for v2 coordination work

---

## Deferred beyond v1

These items are intentionally deferred and must not be treated as part of the minimal v1 scope unless explicitly promoted:

- [ ] Heartbeat-based lock renewal
- [ ] Read/write lock separation
- [ ] Multi-resource transactions
- [ ] Deadlock handling
- [ ] Automatic rollback orchestration
- [ ] Rich operation state tracking
- [ ] Conflict detection across concurrent workflows
- [ ] Optional global/shared coordination layer
- [ ] Full enforcement across arbitrary external tools that do not integrate with Codecortex

---

## Notes

Use this file as the implementation source of truth for the execution transition.

If implementation reality diverges from this checklist, update the checklist explicitly instead of letting the plan drift from the codebase.
