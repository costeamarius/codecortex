# v1 Release Readiness

- **Status:** Accepted
- **Date:** 2026-03-23

## v1 summary

CodeCortex v1 delivers a repository memory system for AI agents together with a minimal deterministic execution substrate.

## What v1 supports

### Repository memory
- repository scanning
- graph building and incremental update
- symbol and impact retrieval
- semantic assertion persistence
- feature slices
- benchmark utilities

### Deterministic execution substrate
- safe file editing through `cortex edit-file`
- repo-context command execution through `cortex run-command`
- validation-before-commit for supported file types
- append-only operation logging
- minimal write locking with TTL
- machine-readable execution results
- repo-local capability exposure through `cortex capabilities`

### Agent alignment
- OpenClaw-aligned runner model
- repo-defined operating model for participating agents
- IDE/OpenClaw parity expectations in supported flows

## What v1 does not support

- heartbeat-based lock renewal
- read/write lock separation
- multi-resource transactions
- deadlock handling
- rollback orchestration
- conflict detection across advanced concurrent workflows
- universal enforcement across arbitrary external tools
- global execution layer

## Functional readiness checklist

- repository memory features operate correctly
- minimal execution path works end-to-end
- validation works for supported file types
- logging works for execution actions
- locking works for single-file write coordination
- Codecortex-enabled repo detection works for supported integrations

## Test status

Current test suite validates:
- repository memory behavior
- execution-layer behavior
- OpenClaw alignment helpers
- participating-agent operating model

## OpenClaw-aligned behavior in v1

OpenClaw should:
- detect Codecortex-enabled repositories
- query repo-local capabilities
- invoke repo-local CodeCortex CLI commands
- consume structured results
- avoid embedding repository execution logic

## Release interpretation

v1 should be understood as:
- a real and usable first release boundary
- minimal by design
- intentionally strict in scope
- ready to serve as the base for coordination improvements in v2
