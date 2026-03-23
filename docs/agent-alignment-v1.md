# Agent Alignment v1

- **Status:** Implemented
- **Date:** 2026-03-23

## Purpose

This document defines the expected behavior of IDE agents and external agents when interacting with Codecortex-enabled repositories.

## Participating agents

A participating agent is any supported agent environment expected to follow the repository-defined CodeCortex operating model.

Examples in v1:
- OpenClaw agents
- Cursor or IDE agents
- local CLI-driven agent runners
- future supported external agents

## Core rule

If a repository is Codecortex-enabled, participating agents must adopt the repo-defined operating model.

## Expected IDE-agent workflow

For Codecortex-enabled repositories, IDE agents should:
- use CodeCortex retrieval before broad manual exploration when practical
- use the repo-local CLI for supported mutations
- align with the same execution path used by OpenClaw

## Expected external-agent workflow

External or remote participating agents should:
- detect Codecortex-enabled repositories
- query repo-local capabilities
- use the same repo-local CLI contract for supported operations
- avoid environment-specific bypass behavior

## Parity expectation

IDE and OpenClaw are different execution environments, but they should expose the same repository-defined operational behavior.

Parity in v1 means:
- same repo-local CLI
- same execution commands
- same result contracts
- same repository-defined mutation path

## Participating agent rules

Participating agents must:
- treat CodeCortex as the repository operating model when enabled
- use `cortex edit-file` for supported file edits
- use `cortex run-command` for supported command execution
- avoid bypassing the repo-local execution layer for supported operations

## Bypass behavior examples

Examples considered bypasses in v1:
- direct file writes outside the execution layer
- skipping repo-local CodeCortex commands for supported operations
- applying environment-specific execution behavior that ignores repository rules

## v1 limitations

- enforcement remains integration-driven
- unsupported external tools may still bypass CodeCortex unless integrated
- this phase defines the operating model, not universal enforcement
