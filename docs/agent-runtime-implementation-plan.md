# CodeCortex Agent Runtime Implementation Plan

Status: Draft tracking document
Source inputs:
- Audit of current implementation gaps
- [ADR-001](/Users/mariuscostea/Documents/codecortex/docs/adr/ADR-001-codecortex-architecture.md)
- [ADR-002](/Users/mariuscostea/Documents/codecortex/docs/adr/ADR-002-minimal-execution-layer-v1.md)
- [ADR-003](/Users/mariuscostea/Documents/codecortex/docs/adr/ADR-003-codecortex-enabled-repositories-define-agent-operating-model.md)
- [execution-contracts-v1.md](/Users/mariuscostea/Documents/codecortex/docs/execution-contracts-v1.md)
- [execution-runtime-v1.md](/Users/mariuscostea/Documents/codecortex/docs/execution-runtime-v1.md)

## Purpose

Bridge the current implementation to the target architecture where CodeCortex is a true agent runtime:

`Agent -> Runtime -> Execution -> Memory Update -> Next Action`

This document is intentionally implementation-focused. It tracks the minimum work required to make the runtime loop real without introducing unnecessary abstraction.

## Audit Issue Index

Use these issue IDs in tasks below.

- `A1`: Memory is not used by execution.
- `A2`: Execution does not update memory.
- `A3`: There is no enforced single execution path.
- `A4`: Repository detection is inconsistent.
- `A5`: Capabilities are static and hardcoded.
- `A6`: Constraints and decisions exist but are not used.
- `A7`: OpenClaw and agent integration are concept-only.
- `A8`: Memory consumption is inconsistent across commands.
- `A9`: Repo-local vs global-runtime boundary is unclear.
- `A10`: Execution substrate claims exceed actual enforcement and policy coverage.

## ADR Component Index

Use these ADR component IDs in tasks below.

- `D1`: Global runtime / repo-local memory boundary from ADR-001.
- `D2`: Single execution path from ADR-002.
- `D3`: Structured action envelope from execution contracts v1.
- `D4`: Repo-local runtime data under `.codecortex/` from execution runtime v1.
- `D5`: Participating-agent operating model from ADR-003.
- `D6`: Minimal deterministic execution layer from ADR-002.
- `D7`: Repo detection and Codecortex-enabled repository rule from ADR-003.

## Working Rules

- Prefer concrete runtime behavior over framework design.
- Extend existing modules where possible before adding new ones.
- Keep constraints simple in the first runtime pass:
  path rules, command rules, repo-state rules.
- Do not build multi-agent coordination beyond the closed loop needed now.
- Do not replace existing graph/execution primitives until the kernel path is real.

## Phase 1: Runtime Foundation (Kernel + Gateway)

Goal: establish a single runtime entry point and make the global-runtime / repo-memory boundary explicit.

### Tasks

- [x] Implement canonical repo detection and binding
  - Priority: CRITICAL
  - Fixes: `A4`, `A9`
  - ADR: `D1`, `D4`, `D7`
  - Dependencies: none
  - Code:
    - Add `codecortex/memory/detection.py`
    - Add `codecortex/memory/repo_state.py`
    - Add `codecortex/memory/state_store.py`
    - Define canonical rule: repo is enabled if `.codecortex/meta.json` exists and is valid
  - Behavior:
    - All runtime actions resolve a single repo root and bind to one authoritative `.codecortex/` state directory
    - `AGENTS.md` and `codecortex/` directory become advisory markers, not authoritative enablement markers
  - Verify:
    - Manually run detection against:
      - repo with only `AGENTS.md`
      - repo with only `.codecortex/`
      - repo with valid `.codecortex/meta.json`
    - Confirm only the valid initialized repo reports enabled

- [x] Add `state.json` as required runtime state
  - Priority: CRITICAL
  - Fixes: `A2`, `A9`
  - ADR: `D4`, `D6`
  - Dependencies: canonical repo detection and binding
  - Code:
    - Extend init flow to create `.codecortex/state.json`
    - Add schema fields:
      - `repo_initialized`
      - `graph_dirty`
      - `last_action_at`
      - `last_action_id`
      - `last_scan_at`
      - `last_scan_commit`
  - Behavior:
    - Runtime has one place to track execution state and graph freshness
  - Verify:
    - Run repo init
    - Confirm `state.json` exists and contains the expected keys

- [x] Introduce runtime request/response models
  - Priority: CRITICAL
  - Fixes: `A3`, `A7`, `A9`
  - ADR: `D1`, `D3`, `D5`
  - Dependencies: none
  - Code:
    - Add `codecortex/runtime/models.py`
    - Define `ActionRequest`, `ActionResponse`, `RuntimeContext`, `PolicyDecision`, `MemoryUpdateResult`
  - Behavior:
    - Runtime boundary becomes typed and explicit
    - CLI and future integrations share one action contract
  - Verify:
    - Add unit tests that serialize and deserialize request/response payloads

- [x] Implement `RuntimeKernel.handle_action()`
  - Priority: CRITICAL
  - Fixes: `A1`, `A2`, `A3`, `A9`
  - ADR: `D1`, `D2`, `D3`, `D6`
  - Dependencies:
    - runtime request/response models
    - canonical repo detection and binding
  - Code:
    - Add `codecortex/runtime/kernel.py`
    - Implement orchestration skeleton:
      - bind repo
      - load repo state
      - build context placeholder
      - evaluate policy placeholder
      - execute through bridge placeholder
      - apply memory feedback placeholder
      - return response
  - Behavior:
    - There is exactly one high-level runtime entry point for supported actions
  - Verify:
    - Call kernel directly in tests with `edit_file`
    - Confirm response envelope includes policy and memory sections even if initially minimal

- [x] Implement `AgentGateway`
  - Priority: CRITICAL
  - Fixes: `A3`, `A7`
  - ADR: `D2`, `D3`, `D5`
  - Dependencies:
    - runtime request/response models
    - `RuntimeKernel.handle_action()`
  - Code:
    - Add `codecortex/runtime/gateway.py`
    - Add one public method that accepts structured action payloads and forwards them to the kernel
  - Behavior:
    - CLI and external agents use one ingress path instead of calling executor helpers directly
  - Verify:
    - Add a test that submits an `edit_file` request through the gateway and confirms it reaches the kernel

- [x] Add `cortex action` as the runtime entry command
  - Priority: CRITICAL
  - Fixes: `A3`, `A7`
  - ADR: `D2`, `D3`, `D5`
  - Dependencies:
    - `AgentGateway`
  - Code:
    - Extend [cortex_cli.py](/Users/mariuscostea/Documents/codecortex/cli/cortex_cli.py)
    - Add:
      - `cortex action --request-file <path>`
      - `cortex action --stdin`
  - Behavior:
    - Agents can use one machine-readable command instead of multiple ad hoc entry points
  - Verify:
    - Pipe JSON into `cortex action --stdin`
    - Confirm structured JSON response

- [x] Route mutating CLI commands through gateway
  - Priority: CRITICAL
  - Fixes: `A3`, `A10`
  - ADR: `D2`, `D3`, `D6`
  - Dependencies:
    - `cortex action`
  - Code:
    - Refactor `edit-file` and `run-command` in [cortex_cli.py](/Users/mariuscostea/Documents/codecortex/cli/cortex_cli.py) to build `ActionRequest` and call the gateway
  - Behavior:
    - CLI mutation path now matches the runtime path
  - Verify:
    - Existing CLI execution tests still pass after being routed through the gateway

- [x] Demote direct executor access to internal-only usage
  - Priority: IMPORTANT
  - Fixes: `A3`, `A10`
  - ADR: `D2`, `D6`
  - Dependencies:
    - mutating CLI commands routed through gateway
  - Code:
    - Update [codecortex/execution/executor.py](/Users/mariuscostea/Documents/codecortex/codecortex/execution/executor.py) docstring and imports
    - Stop treating it as the public boundary
    - Remove public CLI references to `execute_action()`
  - Behavior:
    - Runtime kernel becomes the documented public boundary
  - Verify:
    - Search docs and CLI code to confirm `execute_action()` is not presented as the public agent interface

## Phase 2: Context + Policy Integration

Goal: force execution to consume repo memory and repo rules before acting.

### Tasks

- [x] Implement `ContextBuilder` with merged repo memory loading
  - Priority: CRITICAL
  - Fixes: `A1`, `A8`, `A9`
  - ADR: `D1`, `D4`, `D6`
  - Dependencies:
    - runtime kernel
    - repo state loader
  - Code:
    - Add `codecortex/runtime/context_builder.py`
    - Load:
      - graph
      - semantics
      - constraints
      - recent decisions
      - runtime state
    - Build one `RuntimeContext`
  - Behavior:
    - Execution receives actual repo memory instead of only request payloads
  - Verify:
    - Create a repo with graph, semantics, and decisions
    - Confirm context builder returns all of them in one context object

- [x] Add action-specific context for `edit_file`
  - Priority: CRITICAL
  - Fixes: `A1`, `A8`
  - ADR: `D1`, `D6`
  - Dependencies:
    - `ContextBuilder`
  - Code:
    - Add helper that collects:
      - file node
      - imported_by
      - symbol relations
      - relevant semantic assertions
      - recent decisions touching the file/module
  - Behavior:
    - File mutations can be validated against actual code and memory context
  - Verify:
    - Use a repo with semantic assertions and decisions for a target file
    - Confirm the built context includes them

- [x] Add action-specific context for `run_command`
  - Priority: IMPORTANT
  - Fixes: `A1`, `A10`
  - ADR: `D1`, `D6`
  - Dependencies:
    - `ContextBuilder`
  - Code:
    - Include:
      - repo state
      - graph freshness
      - command classification input
      - relevant command policy rules
  - Behavior:
    - Commands are evaluated in repo context instead of as raw subprocess calls
  - Verify:
    - Inspect built context for a command request and confirm command-policy inputs are present

- [x] Implement a minimal `PolicyEngine`
  - Priority: CRITICAL
  - Fixes: `A1`, `A3`, `A6`, `A10`
  - ADR: `D2`, `D5`, `D6`, `D7`
  - Dependencies:
    - `ContextBuilder`
  - Code:
    - Add `codecortex/runtime/policy_engine.py`
    - Support only three rule families in first pass:
      - repo state rules
      - path rules
      - command rules
  - Behavior:
    - Runtime can block actions before execution
  - Verify:
    - Submit disallowed requests and confirm runtime returns blocked policy result before execution

- [x] Make `constraints.json` executable via policy evaluation
  - Priority: CRITICAL
  - Fixes: `A6`
  - ADR: `D1`, `D4`, `D5`
  - Dependencies:
    - minimal `PolicyEngine`
  - Code:
    - Replace string-only constraints with minimal structured schema:
      - `path_write_rule`
      - `command_rule`
      - `require_fresh_graph`
    - Add parser/validator in `codecortex/memory/constraint_store.py`
  - Behavior:
    - Constraints stop being write-only metadata and become real execution checks
  - Verify:
    - Add a deny rule for writing into `docs/**`
    - Attempt a blocked edit through runtime

- [x] Integrate repo state validation into policy checks
  - Priority: CRITICAL
  - Fixes: `A4`, `A5`, `A10`
  - ADR: `D4`, `D6`, `D7`
  - Dependencies:
    - minimal `PolicyEngine`
    - `state.json`
  - Code:
    - Block or degrade actions when:
      - repo not initialized
      - graph missing
      - graph dirty and action requires fresh graph
  - Behavior:
    - Runtime starts respecting the actual state of repo memory
  - Verify:
    - Mark graph dirty in `state.json`
    - Confirm a graph-dependent action returns warning or blocked result

- [x] Replace hardcoded capabilities with computed capabilities
  - Priority: IMPORTANT
  - Fixes: `A5`
  - ADR: `D1`, `D4`, `D7`
  - Dependencies:
    - repo state validation
    - policy engine
  - Code:
    - Add `codecortex/runtime/capabilities.py`
    - Derive capability snapshot from:
      - repo initialized
      - graph present
      - graph fresh/dirty
      - constraints loaded
      - supported actions
  - Behavior:
    - `cortex capabilities` becomes a runtime health and readiness report
  - Verify:
    - Compare capabilities output for:
      - uninitialized repo
      - initialized repo without graph
      - initialized repo with fresh graph

## Phase 3: Memory Feedback Loop

Goal: make execution update repo memory so the next action sees the changed state.

### Tasks

- [x] Implement `ExecutionBridge`
  - Priority: CRITICAL
  - Fixes: `A1`, `A2`, `A3`
  - ADR: `D2`, `D3`, `D6`
  - Dependencies:
    - runtime kernel
    - policy engine
  - Code:
    - Add `codecortex/runtime/execution_bridge.py`
    - Route approved actions to low-level execution modules only after policy passes
  - Behavior:
    - Kernel controls the handoff into file and command operations
  - Verify:
    - Confirm `edit_file` and `run_command` still work through the kernel after policy approval

- [x] Implement `MemoryFeedback.apply()`
  - Priority: CRITICAL
  - Fixes: `A2`
  - ADR: `D1`, `D4`, `D6`
  - Dependencies:
    - `ExecutionBridge`
    - `state.json`
  - Code:
    - Add `codecortex/runtime/memory_feedback.py`
    - Update:
      - `state.json`
      - operation logs
      - graph freshness flags
      - decision/history store when requested
  - Behavior:
    - Every successful runtime action leaves behind memory changes
  - Verify:
    - Execute `edit_file`
    - Confirm `state.json` and operation log change immediately after action

- [x] Mark graph dirty after successful Python file edits
  - Priority: CRITICAL
  - Fixes: `A2`
  - ADR: `D4`, `D6`
  - Dependencies:
    - `MemoryFeedback.apply()`
  - Code:
    - In feedback loop, detect edits to `.py` files and set `graph_dirty = true`
  - Behavior:
    - Runtime no longer pretends graph memory is fresh after code mutation
  - Verify:
    - Edit a Python file through runtime
    - Confirm `state.json.graph_dirty` becomes `true`

- [x] Add optional automatic incremental graph update after mutating actions
  - Priority: IMPORTANT
  - Fixes: `A2`, `A8`
  - ADR: `D1`, `D4`, `D6`
  - Dependencies:
    - graph dirty marking
  - Code:
    - Add runtime option:
      - mark dirty only
      - or run `update_graph(...)` automatically when safe
  - Behavior:
    - Runtime can close the loop immediately for simple edit cases
  - Verify:
    - Enable auto-update option
    - Edit a Python file
    - Confirm graph commit metadata changes and dirty flag clears

- [x] Turn `decisions.jsonl` into a real store
  - Priority: IMPORTANT
  - Fixes: `A6`
  - ADR: `D1`, `D4`
  - Dependencies:
    - `MemoryFeedback.apply()`
  - Code:
    - Add `codecortex/memory/decision_store.py`
    - Add append + query helpers
    - Refactor `remember` command to use the store
  - Behavior:
    - Decisions become queryable runtime memory instead of write-only text
  - Verify:
    - Record a decision through runtime
    - Query recent decisions for a file/module and confirm it appears

- [x] Align `context` and feature-building flows with merged memory
  - Priority: IMPORTANT
  - Fixes: `A8`
  - ADR: `D1`, `D4`
  - Dependencies:
    - merged context loading
  - Code:
    - Refactor [graph_context.py](/Users/mariuscostea/Documents/codecortex/codecortex/graph_context.py)
    - Refactor [feature_graph.py](/Users/mariuscostea/Documents/codecortex/codecortex/feature_graph.py)
    - Use graph + semantic memory instead of raw graph only
  - Behavior:
    - Memory-backed retrieval becomes consistent across CLI surfaces
  - Verify:
    - Add a semantic assertion and confirm it changes `context` or feature output where relevant

## Phase 4: Agent Integration (OpenClaw)

Goal: replace concept-only integration with a real runtime-facing contract.

### Tasks

- [x] Define the OpenClaw runtime transport contract
  - Priority: CRITICAL
  - Fixes: `A7`
  - ADR: `D3`, `D5`
  - Dependencies:
    - `cortex action`
  - Code:
    - Add `codecortex/integration/openclaw_adapter.py`
    - Document one transport:
      - JSON request in
      - JSON response out
  - Behavior:
    - OpenClaw integration becomes executable, not descriptive
  - Verify:
    - Use a fixture request payload and confirm the adapter calls the gateway and returns runtime JSON

- [x] Require agent identity for mutating actions from participating environments
  - Priority: CRITICAL
  - Fixes: `A3`, `A7`
  - ADR: `D3`, `D5`
  - Dependencies:
    - `PolicyEngine`
    - OpenClaw runtime transport contract
  - Code:
    - Add policy check:
      - if `environment` is participating and action is mutating, require `agent_id`
  - Behavior:
    - Runtime can attribute and govern participating-agent mutations
  - Verify:
    - Submit mutating action from `openclaw` without `agent_id`
    - Confirm blocked result

- [x] Replace static OpenClaw helper payloads with runtime-backed detection and invocation
  - Priority: IMPORTANT
  - Fixes: `A4`, `A7`
  - ADR: `D5`, `D7`
  - Dependencies:
    - canonical repo detection
    - OpenClaw runtime transport contract
  - Code:
    - Refactor [openclaw_integration.py](/Users/mariuscostea/Documents/codecortex/codecortex/openclaw_integration.py)
    - Make it report the canonical runtime state and the `cortex action` contract
  - Behavior:
    - OpenClaw integration points reflect real runtime behavior
  - Verify:
    - Call helper payload generation on initialized and uninitialized repos
    - Confirm the payload reflects actual runtime readiness

- [x] Update generated `AGENTS.md` to point agents to the runtime gateway
  - Priority: IMPORTANT
  - Fixes: `A3`, `A7`
  - ADR: `D2`, `D5`
  - Dependencies:
    - `cortex action`
  - Code:
    - Refactor [agent_instructions.py](/Users/mariuscostea/Documents/codecortex/codecortex/agent_instructions.py)
    - Replace mutation guidance based on direct helper commands with runtime-first guidance
  - Behavior:
    - Generated repo instructions match the intended operating model
  - Verify:
    - Run `init-agent`
    - Confirm generated `AGENTS.md` tells agents to use runtime entrypoints

## Phase 5: Stabilization and Cleanup

Goal: remove ambiguity, verify end-to-end behavior, and delete dead code and claims.

### Tasks

- [x] Add end-to-end runtime loop tests
  - Priority: CRITICAL
  - Fixes: `A1`, `A2`, `A3`, `A7`
  - ADR: `D1`, `D2`, `D3`, `D5`, `D6`
  - Dependencies:
    - phases 1 through 4 core tasks
  - Code:
    - Add integration tests for:
      - `Agent -> action -> kernel -> policy -> execution -> memory feedback`
      - blocked action before execution
      - graph dirty after Python edit
  - Behavior:
    - Runtime loop is proven, not inferred from unit tests
  - Verify:
    - Run the test suite and confirm dedicated end-to-end runtime tests pass

- [x] Remove or deprecate misleading public surfaces
  - Priority: IMPORTANT
  - Fixes: `A3`, `A10`
  - ADR: `D2`, `D5`
  - Dependencies:
    - end-to-end runtime loop tests
  - Code:
    - Deprecate direct public framing of:
      - `execute_action()`
      - static capabilities behavior
      - concept-only OpenClaw helpers
  - Behavior:
    - Public docs and interfaces point to the real runtime path
  - Verify:
    - Search docs and help text for outdated execution-path claims

- [x] Remove unused abstractions and dependencies
  - Priority: IMPORTANT
  - Fixes: `A9`, `A10`
  - ADR: `D1`
  - Dependencies:
    - runtime path stable
  - Code:
    - Remove unused helpers if still dead:
      - `blocked_result`
      - `failure_result`
      - `LockRecord` if not adopted
    - Remove unused dependencies from [pyproject.toml](/Users/mariuscostea/Documents/codecortex/pyproject.toml)
  - Behavior:
    - Codebase reflects actual runtime architecture instead of abandoned paths
  - Verify:
    - Search for remaining references and run tests after cleanup

- [x] Align docs with the implemented runtime boundary
  - Priority: IMPORTANT
  - Fixes: `A7`, `A9`, `A10`
  - ADR: `D1`, `D2`, `D5`
  - Dependencies:
    - runtime loop stable
  - Code:
    - Update:
      - [README.md](/Users/mariuscostea/Documents/codecortex/README.md)
      - architecture docs
      - execution docs
      - OpenClaw docs
  - Behavior:
    - Project claims match what the runtime actually does
  - Verify:
    - Manual review: docs describe the same entrypoint and repo detection rules as the code

## Cross-Phase Dependency Summary

- Canonical repo detection must exist before dynamic capabilities, policy checks, and OpenClaw integration can be made trustworthy.
- `RuntimeKernel.handle_action()` must exist before CLI routing, policy integration, and memory feedback.
- `ContextBuilder` must exist before `PolicyEngine` can use repo memory meaningfully.
- `PolicyEngine` must exist before `ExecutionBridge` becomes a guarded execution path.
- `MemoryFeedback` must exist before the runtime loop is closed.
- `cortex action` must exist before OpenClaw integration becomes real.
- End-to-end tests should be added only after the full kernel -> policy -> execution -> feedback path exists.

## Minimal Path to First Working Runtime

Only the essential tasks required for:

`Agent -> Runtime -> Execution -> Memory loop`

- [ ] Implement canonical repo detection and binding
- [ ] Add `state.json` as required runtime state
- [ ] Introduce runtime request/response models
- [ ] Implement `RuntimeKernel.handle_action()`
- [x] Implement `AgentGateway`
- [x] Add `cortex action` as the runtime entry command
- [x] Route mutating CLI commands through gateway
- [ ] Implement `ContextBuilder` with merged repo memory loading
- [ ] Implement a minimal `PolicyEngine`
- [ ] Make `constraints.json` executable via policy evaluation
- [x] Implement `ExecutionBridge`
- [ ] Implement `MemoryFeedback.apply()`
- [ ] Mark graph dirty after successful Python file edits
- [x] Add end-to-end runtime loop tests

## Anti-Overengineering Guardrails

Do now:
- one kernel
- one gateway
- one context object
- one simple policy engine
- one feedback loop
- one canonical repo detection rule

Do not do yet:
- multi-resource transactions
- heartbeat locking redesign
- policy DSLs
- rollback orchestration
- global coordination services
- advanced semantic inference pipelines
- generalized plugin systems

The first success condition is not elegance. It is this:

`A participating agent can submit one structured action, the runtime uses repo memory before execution, executes through one controlled path, updates repo memory afterward, and returns a machine-readable result.`

## Phase 1 Critical Fixes Implemented

Date: 2026-03-25

The following Phase 1 critical issues were implemented without advancing into Phase 2 work.

### 1. Repo Enablement Enforcement

- `RuntimeKernel.handle_action()` now blocks execution when canonical repo detection does not resolve to a CodeCortex-enabled repository.
- Enforcement is based on the existing canonical rule only: a repository is enabled only if `.codecortex/meta.json` exists and is valid.
- Runtime responses for disabled repositories now return:
  - `status: "blocked"`
  - `policy.allowed: false`
  - `error.error_type: "RepoNotEnabled"`
- This closes the previous gap where mutating commands could still run in repositories that had advisory markers or only a partial `.codecortex/` directory.

### 2. Single Execution Path Enforcement

- The execution layer no longer relies on docstrings alone to imply internal-only usage.
- `codecortex.execution.executor.execute_action()` now rejects calls that do not originate from `RuntimeKernel`.
- `codecortex.execution.file_ops.edit_file_safe()` now rejects calls that do not originate from the execution executor.
- `codecortex.execution.command_ops.run_command_safe()` now rejects calls that do not originate from the execution executor.
- This makes the runtime kernel the enforced execution ingress for supported actions instead of merely the documented one.

### 3. Real Runtime State Updates

- `RuntimeKernel._apply_memory_feedback()` now writes real updates to `.codecortex/state.json` after execution.
- The runtime state loader now normalizes missing or invalid state payloads back to the required initial schema before applying updates.
- After each executed action, the runtime updates:
  - `repo_initialized`
  - `last_action_at`
  - `last_action_id`
- After a successful `edit_file`, the runtime also sets:
  - `graph_dirty: true`
- The runtime response `memory` section now reports `applied: true` and returns the concrete state fields that were updated.

### Verification Added

- Added tests that confirm repositories without valid `.codecortex/meta.json` are blocked by the kernel and CLI mutation path.
- Added tests that confirm direct calls to `execute_action()`, `edit_file_safe()`, and `run_command_safe()` are rejected as runtime bypass attempts.
- Added tests that confirm successful runtime actions write updated values into `.codecortex/state.json`.

## Phase 2 Fixes Implemented

Date: 2026-03-25

The following fixes were applied after strict validation of Phase 2. These changes close enforcement gaps that previously allowed the runtime to claim Phase 2 behavior without actually enforcing it.

### 1. Invalid Runtime State Now Blocks Execution

- `ContextBuilder` no longer treats missing or invalid `.codecortex/state.json` as a valid initialized runtime state.
- Missing or invalid runtime state is now surfaced as:
  - `repo_initialized: false`
  - `state_valid: false`
- `PolicyEngine` now blocks actions when runtime state is missing or invalid before execution occurs.
- This closes the previous gap where a repository with valid `.codecortex/meta.json` but no valid `state.json` could still mutate files or run commands.

### 2. Path Rules Now Apply To Normalized Repo Paths

- `edit_file` policy evaluation no longer matches rules against the raw user-supplied path.
- Absolute paths that point inside the repository are now normalized into repo-relative paths before:
  - action context construction
  - path policy evaluation
- This closes the bypass where a deny rule such as `docs/**` could be defeated by sending an absolute path like `/repo/docs/file.md`.

### 3. Command Policy Now Evaluates The Effective Command

- `run_command` policy evaluation no longer relies only on the wrapper argv used by the CLI.
- When the CLI sends commands as `bash -lc <command>`, the runtime now extracts the effective user command and classifies that command for policy checks.
- `deny_program` and `deny_family` rules are now evaluated against the effective command instead of only the shell wrapper.
- This closes the gap where a rule blocking `python3` could be bypassed because policy only saw `bash`.

### 4. Constraint Validation Was Made Explicit

- Added explicit constraint validation in `codecortex.memory.constraint_store`.
- Invalid shapes in `constraints.json` are now reported as validation issues instead of being silently treated as acceptable input.
- `normalize_constraints_store()` now falls back to the default structured constraint set when the payload is missing or not a JSON object.
- This makes the constraint layer executable and inspectable instead of partially best-effort and partially silent.

### 5. Capability Reporting Was Aligned With Actual Enforcement

- `build_capabilities_snapshot()` now reports `constraint_issues` when `constraints.json` contains invalid entries.
- Capability warnings now distinguish between:
  - missing or invalid constraint files using default fallback constraints
  - present constraint files that contain invalid entries
- This removes the previous mismatch where capabilities claimed one policy state while runtime enforcement used another.

### Verification Added

- Added tests that confirm missing `state.json` causes the kernel and CLI mutation path to return blocked policy results.
- Added tests that confirm absolute in-repo file paths still trigger deny path rules such as `docs/**`.
- Added tests that confirm shell-wrapped commands are blocked when the effective program violates command policy.
- Added tests that confirm context building normalizes absolute edit targets and extracts effective command context from shell wrappers.
- Added tests that confirm invalid constraint payloads are reported and that default constraint fallback behavior is visible in capabilities output.

## Phase 3 Fixes Implemented

Date: 2026-03-25

The following fixes were applied after strict validation of Phase 3. These changes close the remaining gaps where the runtime partially updated repo memory but still failed to enforce the full execution -> memory feedback loop required before Phase 4.

### 1. Kernel-Controlled Execution Handoff Is Now Enforced

- `codecortex.runtime.execution_bridge.ExecutionBridge` no longer acts as a thin convenience wrapper around the execution layer.
- The bridge now rejects direct calls that do not originate from `RuntimeKernel`.
- The bridge now performs the actual handoff into:
  - `edit_file_safe()`
  - `run_command_safe()`
- This closes the previous gap where internal callers could bypass policy by invoking the execution bridge directly.

### 2. Mutating Commands Now Update Graph Freshness Correctly

- `codecortex.execution.command_ops.run_command_safe()` now snapshots Python files before and after command execution.
- Successful `run_command` actions now report concrete `changed_python_files` in their execution result.
- `codecortex.runtime.memory_feedback.MemoryFeedback` now uses those changed files to mark `state.json.graph_dirty = true` when commands mutate Python code.
- This closes the previous gap where arbitrary commands could mutate repository code while runtime memory still claimed the graph was fresh.

### 3. Auto Graph Update Now Works For Any Safe Mutating Runtime Action

- Automatic graph refresh is no longer limited in practice to the `edit_file` path.
- When `auto_update_graph` is requested and a successful runtime action reports changed Python files, the feedback loop now attempts incremental graph refresh.
- On success, the runtime now updates:
  - `last_scan_at`
  - `last_scan_commit`
  - `graph_dirty: false`
- On failure to refresh because the graph is missing or invalid, the runtime now keeps the graph marked dirty instead of pretending the memory loop is closed.

### 4. Decision Memory Is Now Part Of Runtime Feedback

- `codecortex.runtime.memory_feedback.MemoryFeedback` now writes to `.codecortex/decisions.jsonl` when the action payload explicitly includes a `decision` object.
- Stored decision entries are normalized through `codecortex.memory.decision_store.append_decision()`.
- Runtime feedback now enriches stored decision entries with:
  - `timestamp`
  - `git_commit`
  - `action`
  - `agent_id` when present
  - target file/command reference when applicable
- This closes the previous gap where decisions remained a CLI-only side channel instead of queryable runtime memory produced by execution.

### 5. CLI Command Execution Was Aligned With The Fixed Feedback Loop

- `cortex run-command` now accepts `--auto-update-graph`.
- This keeps command execution behavior aligned with the same feedback-loop options already available on `edit-file`.
- The CLI can now request immediate graph refresh after successful command-driven Python mutations instead of only marking the graph dirty.

### Verification Added

- Added tests that confirm direct calls to `ExecutionBridge.execute()` are rejected as runtime bypass attempts.
- Added tests that confirm successful mutating commands mark `state.json.graph_dirty` and return the changed Python files in runtime memory feedback.
- Added tests that confirm runtime actions with a `decision` payload append normalized entries into `.codecortex/decisions.jsonl`.
- Added tests that confirm command-driven Python mutations can trigger automatic incremental graph refresh through the CLI.

## Phase 4 Fixes Implemented

Date: 2026-03-25

The following fixes were applied after strict validation of Phase 4. These changes close the remaining contract gap in the OpenClaw runtime transport and remove stale guidance that still pointed participating agents at the pre-runtime execution path.

### 1. OpenClaw Adapter Now Returns Real JSON Egress

- `codecortex.integration.openclaw_adapter.OpenClawRuntimeAdapter` no longer returns Python dictionaries from its transport-facing methods.
- `handle_json()` now accepts JSON input and returns a serialized JSON response string.
- `handle_payload()` now also returns serialized JSON so the adapter contract is consistently JSON out.
- This closes the mismatch where the transport metadata declared `application/json` egress but the implementation exposed an in-process Python object instead.

### 2. Transport Tests Now Validate Serialized JSON Egress

- `tests/test_openclaw_integration.py` no longer treats adapter responses as Python dictionaries.
- The transport tests now assert that adapter egress is a JSON string and explicitly parse it before validating response fields.
- Added coverage for both JSON-string ingress and direct payload ingress to ensure both adapter entrypoints honor the same JSON-out contract.

### 3. Participating-Agent Guidance Was Aligned With Runtime-First Execution

- `codecortex.agent_operating_model.required_codecortex_operations()` no longer tells participating agents to use `cortex edit-file` or `cortex run-command` as the primary contract.
- The operating-model guidance now points agents to the runtime gateway via `cortex action` and structured JSON request envelopes.
- This removes the remaining Phase 4 guidance mismatch between the shared operating-model helper and the generated `AGENTS.md` instructions.

### Verification Added

- Added tests that confirm the OpenClaw adapter returns serialized JSON, not Python dictionaries.
- Added tests that confirm both adapter ingress paths produce valid JSON egress.
- Updated operating-model tests to confirm runtime-first guidance and to reject stale helper-command expectations.
