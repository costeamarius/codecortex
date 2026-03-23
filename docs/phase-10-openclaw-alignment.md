# Phase 10 OpenClaw Alignment

- **Status:** Implemented
- **Date:** 2026-03-22

## Implemented in this phase

- repo-local OpenClaw alignment helper module
- Codecortex-enabled repository detection helper
- OpenClaw integration payload describing expected runner behavior
- bootstrap-step guidance for OpenClaw wrappers
- documentation for runner model, bootstrap model, and behavior parity

## v1 notes

- OpenClaw remains a runner/integration layer
- CodeCortex remains the owner of repository behavior
- OpenClaw should switch into Codecortex-aware mode when a repo is enabled
- machine-readable `cortex capabilities` output is the first CLI surface for this alignment
