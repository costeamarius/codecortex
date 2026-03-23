# Phase 7 Minimal Locking (v1)

- **Status:** Implemented
- **Date:** 2026-03-22

## Implemented in this phase

- explicit write-lock model
- owner field behavior
- TTL/expiry behavior
- lock file naming strategy
- local lock storage under `.codecortex/locks/`
- expired lock replacement during acquisition
- tests for acquire / release / replace behavior

## v1 lock rules

- only write locks are implemented
- one writer per file resource
- active write locks block concurrent writes
- expired locks may be replaced on the next acquire attempt
- no heartbeat in v1
- no read locks in v1

## Lock file format

```json
{
  "resource": "config.json",
  "owner": "agent_id",
  "created_at": "...",
  "expires_at": "..."
}
```

## v1 limitations

- no read/write lock separation
- no deadlock handling
- no heartbeat renewal
- no multi-resource coordination
