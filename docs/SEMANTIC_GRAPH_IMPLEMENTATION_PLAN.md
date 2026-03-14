# Semantic Graph Implementation Plan

Purpose: track the work required to evolve CodeCortex from a Python import graph into a semantic repository graph that supports low-token, low-iteration AI impact analysis.

Status legend:
- `[ ]` not started
- `[~]` in progress
- `[x]` completed
- `[-]` deferred / optional

## Target Outcome

CodeCortex should let an AI agent answer questions such as:
- what is the impact of changing a feature entry point
- which views, forms, models, and utility functions participate in a flow
- which profile or entity types support a capability and which do not

without requiring repeated prompt refinement or broad manual repository scanning.

## Current State Snapshot

Observed in the current implementation:
- graph schema is file/module oriented
- scanner parses Python AST
- extracted relations are limited to imports
- query/context flows are useful for file routing, not semantic impact analysis

Current limitations:
- no class/function/method nodes
- no call graph
- no inheritance graph
- no framework-aware semantic extraction
- no compact impact-oriented query surface

## Phase 0: Baseline And Acceptance Criteria

- [ ] Define success criteria for "impact analysis works"
- [ ] Select 3 benchmark questions from real repositories
- [ ] Record current baseline:
  - average number of agent queries needed
  - approximate token cost
  - number of missed dependencies
- [ ] Add a simple benchmark fixture or script for repeatable comparison

Notes:
- Suggested benchmark domains:
  - featured portfolio impact
  - image moderation flow
  - user deletion / cleanup side effects

## Phase 1: Graph Schema v2

Goal: extend the graph from file/module-only to symbol-aware.

- [x] Define graph schema version bump strategy (`1.2` for the first semantic iteration)
- [x] Add node types:
  - `file`
  - `module`
  - `class`
  - `function`
  - `method`
- [x] Add edge types:
  - `defines`
  - `imports`
  - `inherits`
  - `calls`
  - `decorated_by`
  - `references` or `uses_symbol`
- [x] Define required metadata per node:
  - stable id
  - name
  - qualified name
  - file path
  - line number
- [x] Define required metadata per edge:
  - source
  - target
  - type
  - line number
  - confidence or resolution mode where helpful
- [x] Update architecture docs to reflect the new schema

Design constraints:
- Keep the schema generic for Python first
- Do not encode Django-specific semantics in the base schema
- Preserve room for future language plugins

## Phase 2: Generic Python Symbol Extraction

Goal: build a reliable symbol graph before adding framework semantics.

- [x] Extend scanner to extract top-level classes
- [x] Extend scanner to extract top-level functions
- [x] Extend scanner to extract methods inside classes
- [x] Extract inheritance relationships from class bases
- [x] Extract decorators on classes/functions/methods
- [x] Extract basic call relationships:
  - local function calls
  - imported symbol calls when directly resolvable
  - method calls within the same class/file when directly resolvable
- [x] Build qualified symbol names consistently
- [x] Handle nested scopes conservatively
- [x] Decide fallback behavior for unresolved dynamic calls
- [x] Add tests for symbol extraction and graph generation

Implementation notes:
- Prefer best-effort resolution over fake precision
- Mark uncertain relationships clearly instead of over-asserting

## Phase 3: Graph Builder And Incremental Update

Goal: make graph generation and refresh support the richer schema.

- [x] Refactor graph builder to ingest symbol records, not only import records
- [x] Generate symbol nodes and symbol edges
- [x] Preserve existing import graph behavior
- [x] Update graph cleanup logic for symbol nodes
- [x] Update incremental refresh to invalidate symbol-level data for changed files
- [x] Rebuild dependent edges safely when symbols disappear or move
- [ ] Ensure old graphs fail gracefully or migrate cleanly
- [x] Add regression tests for full scan and incremental update

## Phase 4: Query And Context v2

Goal: make the richer graph useful to agents with compact retrieval.

- [x] Extend `cortex query` to search:
  - symbol names
  - qualified names
  - edge types
  - node types
- [x] Extend `cortex context <file>` to return:
  - symbols defined in the file
  - inbound/outbound symbol relationships
  - file-level imports as today
- [x] Add `cortex symbol <name>` command
- [x] Add `cortex impact <symbol-or-file>` command
- [ ] Add optional filters:
  - `--type`
  - `--edge`
  - `--depth`
  - `--json`
- [x] Ensure outputs are compact enough for AI prompt injection
- [x] Add tests for retrieval ergonomics and output stability

Success criteria:
- an agent should be able to request a small subgraph instead of broad file dumps

## Phase 5: Django Semantic Plugin

Goal: layer framework-specific understanding on top of the generic Python graph.

- [x] Create a Django-specific semantic extractor module
- [x] Detect Django models via inheritance patterns
- [x] Detect Django forms / ModelForms via inheritance patterns
- [x] Detect `Meta.model` bindings
- [x] Detect view functions and class-based views
- [x] Detect view-to-form relations
- [x] Detect view-to-model relations when explicit
- [x] Detect view-to-template relations when explicit
- [x] Detect delegation to shared utility functions
- [x] Emit semantic edges such as:
  - `binds_model`
  - `uses_form`
  - `uses_template`
  - `delegates_to`
  - `is_django_model`
  - `is_django_form`
  - `is_django_view`
- [x] Add tests against a representative Django fixture app

Important:
- Keep Django logic separate from the generic Python extractor
- Make it possible to disable framework plugins

## Phase 6: Capability And Feature Assertions

Goal: represent relations that are important for impact analysis but not always safely inferable from AST alone.

- [x] Define a storage format for curated semantic assertions
- [x] Decide whether assertions live in:
  - `.codecortex/features.json`
  - a new `.codecortex/semantics.json`
  - structured notes in `.codecortex/notes/`
- [x] Support assertions such as:
  - `supports_feature`
  - `does_not_support_feature`
  - `related_feature`
  - `entry_point_for`
- [x] Add CLI support to inspect these assertions
- [x] Define merge rules between inferred and curated relations
- [x] Add tests for deterministic behavior
- [x] Make assertion persistence append-only with rebuild support to avoid lost writes

Why this matters:
- some impact-critical knowledge is architectural, not syntactically explicit
- this replaces ad hoc docs as a machine-retrievable layer

## Phase 7: Benchmarks And Validation

Goal: prove the new graph reduces token cost and follow-up prompts.

- [~] Re-run the baseline benchmark questions
- [~] Compare:
  - prompt count
  - token cost
  - graph slice size
  - missed dependencies
- [ ] Validate on at least one non-Django Python repository
- [x] Document observed wins and remaining blind spots
- [ ] Decide whether additional plugins are justified

Target improvements:
- fewer iterative prompts
- smaller retrieval payloads
- higher first-answer completeness

## Suggested File-Level Work Breakdown

Likely files to modify:
- [ ] `codecortex/codecortex/scanner.py`
- [ ] `codecortex/codecortex/graph_builder.py`
- [ ] `codecortex/codecortex/graph_context.py`
- [ ] `codecortex/codecortex/graph_status.py`
- [ ] `codecortex/codecortex/feature_graph.py`
- [ ] `codecortex/cli/cortex_cli.py`
- [ ] `odecortex/docs/architecture.md`

Likely new files:
- [ ] `codecortex/codecortex/symbols.py`
- [ ] `codecortex/codecortex/symbol_resolution.py`
- [ ] `odecortex/codecortex/django_semantics.py`
- [ ] `odecortex/tests/test_symbol_graph.py`
- [ ] `codecortex/tests/test_incremental_symbol_update.py`
- [ ] `codecortex/tests/test_django_semantics.py`

## Recommended Implementation Order

1. [ ] Schema v2
2. [ ] Generic Python symbol extraction
3. [ ] Graph builder and incremental update
4. [ ] Query/context v2
5. [ ] Django semantic plugin
6. [ ] Capability assertions
7. [ ] Benchmarks and validation

Reasoning:
- generic symbol extraction unlocks the largest ROI
- Django should be a plugin, not the foundation
- impact analysis quality depends as much on retrieval shape as on extraction quality

## Progress Log

Use this section for short dated updates during implementation.

- [x] 2026-03-13: created implementation tracking document
- [x] 2026-03-13: implemented schema `1.2` with symbol nodes (`class`, `function`, `method`) and semantic edges (`defines`, `inherits`, `calls`, `decorated_by`)
- [x] 2026-03-13: extended `context` and `status` to expose symbol-level information
- [x] 2026-03-13: added regression tests for symbol extraction and incremental update cleanup
- [x] 2026-03-13: reduce query/context payload size for AI-friendly subgraph retrieval
- [x] 2026-03-13: add `query --edge/--limit`, `symbol`, and `impact` commands for compact subgraph retrieval
- [x] 2026-03-13: add Django semantic extraction for explicit model/form/view/template/delegation relations
- [x] 2026-03-13: add benchmark commands for `query`, `symbol`, and `impact` payload size estimation
- [x] 2026-03-13: add `.codecortex/semantics.json` with CLI support and merged retrieval for persisted semantic assertions
- [x] 2026-03-13: switch semantic assertion persistence to append-only journal + rebuild materialization

## Resume Checklist

When resuming after interruption:
- [ ] Read this file first
- [ ] Check the last completed phase
- [ ] Check open items in the current phase
- [ ] Check whether schema changes already landed
- [ ] Run tests relevant to the current phase
- [ ] Update the progress log before stopping
