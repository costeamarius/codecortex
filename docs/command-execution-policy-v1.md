# Command Execution Policy v1

- **Status:** Accepted for implementation
- **Date:** 2026-03-22

## Decision

Command allowlisting is deferred in v1.

## v1 constraints

- commands must execute in repo context
- commands must use the repo-local execution layer
- stdout/stderr must be captured
- non-zero exit codes must return structured failure
- command execution must be logged

## Rationale

The current priority is to establish a deterministic, structured command path before introducing a stricter policy engine.

A future version may introduce:
- allowlisting
- command classes
- policy-based restrictions
- environment-specific command controls
