# Token Efficiency Benchmark Plan

- **Status:** Planned
- **Date:** 2026-03-23

## Purpose

This document defines the benchmark work needed to demonstrate the user-facing value of CodeCortex in terms of token-efficiency and reduced repeated repository exploration cost.

The goal is not only to benchmark technical behavior, but to produce evidence that CodeCortex helps reduce AI context size and token consumption in realistic repository workflows.

## Why this matters

One of the main promises of CodeCortex is that agents should not need to repeatedly rediscover repository structure from scratch.

Instead of paying the context cost of broad repository exploration in every session or task, agents should be able to query focused repository memory.

This should create measurable value in:
- reduced input context size
- reduced repeated scanning/reasoning overhead
- lower approximate token consumption
- more compact task-relevant retrieval

## Primary questions

These benchmarks should help answer:
- how many tokens can CodeCortex save compared to broad manual repository exploration?
- how much smaller is a CodeCortex retrieval payload than raw code context?
- how much repeated repository-understanding cost is avoided across sessions?
- how focused is the returned context relative to the naive baseline?

## Benchmark categories

### 1. Query compression benchmark

Compare:
- naive raw repository exploration for a query
- CodeCortex `query` output

Measure:
- bytes
- characters
- estimated tokens
- reduction percentage

Example question:
- “Find graph builder related functions and dependencies.”

## 2. Symbol compression benchmark

Compare:
- raw source neighborhood around a symbol
- CodeCortex `symbol` output

Measure:
- estimated tokens for raw source context
- estimated tokens for CodeCortex symbol payload
- reduction percentage

Example:
- `codecortex.graph_builder.build_graph`

## 3. Impact compression benchmark

Compare:
- naive exploration of files likely affected by a change
- CodeCortex `impact` output

Measure:
- files considered in naive approach
- files returned by focused impact output
- estimated tokens in each path
- reduction percentage

Example:
- change impact for `codecortex/graph_builder.py`

## 4. Context retrieval benchmark

Compare:
- opening and scanning the raw file manually
- CodeCortex `context` output

Measure:
- raw file token estimate
- context payload token estimate
- retrieval focus ratio

## 5. Repeated session savings benchmark

Measure repository-understanding cost over time.

Compare:
- initial scan / broad exploration cost
- repeated retrieval-only task cost over multiple sessions or tasks

Goal:
Demonstrate that repository memory amortizes the cost of understanding the repository.

Suggested outputs:
- first-use cost
- repeated-use cost
- estimated savings after N tasks

## 6. Task-oriented benchmark

Compare real agent tasks in two modes:

### Baseline
- broad repository exploration
- manual file inspection
- no persistent repository memory

### CodeCortex-assisted
- focused retrieval through CodeCortex
- use of stored repository memory

Measure:
- raw context size
- focused context size
- estimated token reduction
- number of files avoided
- retrieval specificity

Example tasks:
- “What breaks if I change this file?”
- “Where is this symbol used?”
- “Which modules depend on this component?”
- “What is the relevant context for editing this config?”

## Metrics to report

Recommended benchmark outputs:
- `raw_bytes`
- `raw_chars`
- `raw_estimated_tokens`
- `codecortex_bytes`
- `codecortex_chars`
- `codecortex_estimated_tokens`
- `estimated_tokens_saved`
- `reduction_percent`
- `files_considered`
- `files_returned`
- `focus_ratio`

## User-facing value claims supported by these benchmarks

These benchmarks should support claims such as:

- CodeCortex reduces repeated repository exploration cost.
- CodeCortex returns more compact context than naive raw code loading.
- CodeCortex lowers approximate token usage for repository understanding tasks.
- CodeCortex improves context focus by returning structured, task-relevant retrieval.

## Suggested CLI direction

Possible future benchmark commands:

```bash
cortex benchmark query ...
cortex benchmark symbol ...
cortex benchmark impact ...
cortex benchmark context ...
cortex benchmark session-savings ...
```

The existing benchmark surface can be expanded rather than replaced.

## Recommended implementation order

1. query compression benchmark refinement
2. symbol compression benchmark refinement
3. impact compression benchmark refinement
4. context retrieval benchmark
5. repeated session savings benchmark
6. task-oriented benchmark suite

## Notes

Execution benchmarks and token-efficiency benchmarks are related but distinct.

- execution benchmarks measure operational overhead
- token-efficiency benchmarks measure user-facing repository-memory value

Both matter, but token-efficiency benchmarks are the ones most directly useful for explaining the cost-saving value of CodeCortex to users.
