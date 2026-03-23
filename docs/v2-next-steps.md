# v2 Next Steps

- **Status:** Draft
- **Date:** 2026-03-23

## Goal

Build on the v1 deterministic substrate with stronger coordination behavior.

## Planned v2 priorities

1. heartbeat-based lock renewal
2. read/write lock separation
3. improved stale-lock handling
4. better retry strategies for blocked agents
5. stronger CLI ergonomics for execution commands
6. richer capability reporting for external agents and OpenClaw

## Design principle

v2 should extend the v1 operating model without breaking:
- repo-local architecture
- single execution path
- repo-defined behavior
- OpenClaw and IDE parity
