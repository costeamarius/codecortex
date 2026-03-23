# Execution Benchmark Plan

- **Status:** Planned
- **Date:** 2026-03-23

## Purpose

The current benchmark surface focuses primarily on repository-memory retrieval.

After introducing the deterministic execution substrate, CodeCortex also needs benchmark coverage for execution-path cost and behavior.

This document captures the benchmark work that should be added after the v1 implementation cycle.

## Why this is needed

The current benchmark commands are still useful for:
- graph query payloads
- symbol retrieval
- impact retrieval

However, they do not measure the cost of:
- safe file mutation
- validation-before-commit
- lock acquisition and replacement
- operation logging
- repo-context command execution

As a result, the benchmark surface is now incomplete relative to the actual product.

## Benchmark goals

Future execution benchmarks should help answer:
- how much latency does `edit_file_safe(...)` add?
- what is the validation cost for supported file types?
- what overhead is introduced by minimal locking?
- what overhead is introduced by append-only logging?
- what is the wrapper cost of `run_command_safe(...)` relative to raw command execution?
- how does execution performance scale with file size?

## Proposed benchmark areas

### 1. File edit benchmark

Measure:
- total `edit_file_safe(...)` latency
- validation time
- backup creation time
- atomic write time
- diff generation overhead

Suggested scenarios:
- small JSON file
- medium Python file
- large text/config file

### 2. Validation benchmark

Measure:
- JSON validation cost
- Python compile validation cost
- no-validator pass-through cost

Suggested output:
- average latency
- min/max latency
- validator type
- file size

### 3. Lock benchmark

Measure:
- lock acquire latency
- lock release latency
- expired lock replacement latency
- blocked lock response cost

Suggested scenarios:
- no existing lock
- active lock present
- expired lock present

### 4. Logging benchmark

Measure:
- append-only log write latency
- impact of large log detail payloads
- repeated operation logging cost over N operations

### 5. Command execution benchmark

Measure:
- wrapper overhead of `run_command_safe(...)`
- stdout/stderr capture overhead
- cost difference between short and longer-running commands

Suggested scenarios:
- trivial command (`true`, `echo`, or Python print)
- command with output
- command with failure return code

### 6. CLI execution benchmark

Measure:
- `cortex edit-file` end-to-end overhead
- `cortex run-command` end-to-end overhead
- JSON serialization / output cost

## Suggested CLI shape

Possible future commands:

```bash
cortex benchmark exec edit-file ...
cortex benchmark exec run-command ...
cortex benchmark exec validate ...
cortex benchmark exec lock ...
cortex benchmark exec log ...
```

This can coexist with the existing retrieval-oriented benchmark surface.

## Non-goals

This benchmark plan does not require:
- full concurrency benchmarking in v1
- distributed multi-agent performance simulation
- lock fairness analysis
- system-wide stress testing

Those can come later once v2 coordination is in progress.

## Recommended implementation order

1. file edit benchmark
2. validation benchmark
3. command execution benchmark
4. lock benchmark
5. logging benchmark
6. CLI end-to-end benchmark

## Success criteria

This benchmark work should produce:
- a measurable baseline for execution-path latency
- visibility into validation and locking overhead
- a clearer picture of execution cost alongside repository-memory retrieval cost
- better data for deciding future optimization priorities
