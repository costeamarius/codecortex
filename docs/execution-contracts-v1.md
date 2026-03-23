# Execution Contracts v1

- **Status:** Accepted for implementation
- **Date:** 2026-03-22
- **Scope:** Minimal execution contracts for ADR-002 v1.

## Purpose

This document defines the minimal structured contracts for the repo-local execution layer.

The goal is to ensure that supported agents do not send free-form mutation requests, but instead use predictable, machine-readable action and result shapes.

---

## 1. Supported v1 actions

The minimal v1 execution layer supports the following action families:

- `edit_file`
- `run_command`

These actions are intentionally narrow.

---

## 2. Common action envelope

All execution actions use a common envelope.

```json
{
  "action": "edit_file",
  "repo": "/path/to/repo",
  "agent_id": "optional-agent-id",
  "environment": "optional-environment-id",
  "payload": { ... }
}
```

### Fields

- `action`: required action name
- `repo`: required repository root path
- `agent_id`: optional logical agent identifier
- `environment`: optional execution environment identifier (for example `openclaw`, `cursor`, `local_cli`)
- `payload`: required action-specific payload

---

## 3. `edit_file` action contract

### Input

```json
{
  "action": "edit_file",
  "repo": "/path/to/repo",
  "agent_id": "openclaw-agent-1",
  "environment": "openclaw",
  "payload": {
    "file": "config.json",
    "content": "{\n  \"timeout\": 30\n}\n",
    "validate": true,
    "lock_ttl_seconds": 30
  }
}
```

### Required payload fields

- `file`: repo-relative target path
- `content`: full target content

### Optional payload fields

- `validate`: default `true`
- `lock_ttl_seconds`: default implementation-defined v1 TTL

### v1 note

For v1, `edit_file` uses full-content replacement.
Structured patch operations can be introduced later.

---

## 4. `run_command` action contract

### Input

```json
{
  "action": "run_command",
  "repo": "/path/to/repo",
  "agent_id": "cursor-agent-2",
  "environment": "cursor",
  "payload": {
    "command": ["python", "-m", "pytest", "-q"],
    "timeout_seconds": 60
  }
}
```

### Required payload fields

- `command`: command as argument list

### Optional payload fields

- `timeout_seconds`: optional timeout for execution

---

## 5. Common result envelope

All action results use a common envelope.

```json
{
  "status": "success",
  "action": "edit_file",
  "details": { ... }
}
```

### Status values in v1

- `success`
- `failure`
- `blocked`
- `not_implemented`

---

## 6. Success result contract

### Example: `edit_file`

```json
{
  "status": "success",
  "action": "edit_file",
  "details": {
    "file": "config.json",
    "validation": {
      "passed": true,
      "validator": "json",
      "errors": []
    },
    "backup_path": "/repo/config.json.bak",
    "diff": "optional diff or summary"
  }
}
```

### Example: `run_command`

```json
{
  "status": "success",
  "action": "run_command",
  "details": {
    "command": ["python", "-m", "pytest", "-q"],
    "returncode": 0,
    "stdout": "...",
    "stderr": ""
  }
}
```

---

## 7. Failure result contract

```json
{
  "status": "failure",
  "action": "edit_file",
  "details": {
    "error_type": "ValidationError",
    "message": "Validation failed before commit.",
    "validation": {
      "passed": false,
      "validator": "json",
      "errors": ["..."]
    }
  }
}
```

Failure output should be structured and safe for machine consumption.

---

## 8. Blocked result contract

Blocked results are used when a resource cannot currently be mutated because a write lock exists.

```json
{
  "status": "blocked",
  "action": "edit_file",
  "details": {
    "resource": "config.json",
    "owner": "agent_id",
    "retry_after_seconds": 10
  }
}
```

---

## 9. Validation result contract

```json
{
  "passed": true,
  "validator": "json",
  "errors": []
}
```

### Rules

- `passed`: required boolean
- `validator`: optional validator name
- `errors`: list of validation errors

---

## 10. Error model

v1 execution-layer error families:

- `PathViolationError`
- `ValidationError`
- `LockConflictError`
- `CommandExecutionError`
- `ExecutionError` (base type)

### Rules

- validation failures must return `failure`
- lock conflicts must return `blocked`
- unsupported actions may return `not_implemented`
- failures should not expose raw unstructured trace output in the main contract

---

## 11. CLI contract direction

The repo-local CLI is the canonical interface for participating agents.

Planned execution commands:
- `edit-file`
- `run-command`

Command naming is intentionally explicit and action-oriented.

The CLI should support machine-readable output for participating agents.

---

## 12. Operating contract discovery

For v1, agents discover the supported operating model through a combination of:

- repo-local CodeCortex presence
- repo-local CLI availability
- repository instructions
- repository documentation

A richer explicit machine-readable capability report may be added later.

---

## 13. Summary

v1 contracts are intentionally small.

They are designed to be:
- deterministic
- machine-readable
- repo-local
- compatible with OpenClaw-aligned operation
- easy to extend in later coordination phases
