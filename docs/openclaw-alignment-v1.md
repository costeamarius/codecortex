# OpenClaw Alignment v1

- **Status:** Implemented
- **Date:** 2026-03-22

## Purpose

This document defines how OpenClaw aligns with CodeCortex in v1.

## Core rule

OpenClaw is an integration and runner layer.
It must not become the owner of repository behavior.

When a repository is Codecortex-enabled, OpenClaw should adopt the repo-defined operating model.

## Runner model

OpenClaw responsibilities in v1:
- detect whether the target repository is Codecortex-enabled
- bootstrap CodeCortex when missing
- invoke the repo-local CLI
- consume machine-readable results

OpenClaw must not:
- implement file mutation logic
- implement validation logic
- implement locking logic
- bypass the repo-local execution path for supported operations

## Expected invocation examples

```bash
cortex capabilities --path /repo
cortex edit-file --path /repo --file config.json --content '{"timeout": 30}'
cortex run-command --path /repo --command 'python3 -m unittest -q'
```

## Bootstrap model

Recommended v1 flow:

1. detect CodeCortex markers in the target repository
2. if missing, bootstrap CodeCortex into the repo
3. query `cortex capabilities --path <repo>`
4. switch the agent into Codecortex-aware mode
5. use repo-local CodeCortex interfaces for supported operations

## Codecortex-aware behavior

When OpenClaw detects a Codecortex-enabled repository, it should:
- prefer CodeCortex retrieval before broad manual exploration
- use `cortex edit-file` for supported file mutations
- use `cortex run-command` for supported command execution
- treat the repository as repo-defined, not environment-defined

## IDE parity

The expected behavior should match the IDE-side operating model:
- same repo-local interface
- same execution path
- same repository-defined rules

## v1 limitations

- OpenClaw policy enforcement is integration-driven, not globally enforced
- bootstrap flow is documented but still simple
- no background OpenClaw-specific policy engine is introduced in CodeCortex
