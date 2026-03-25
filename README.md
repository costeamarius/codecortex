# CodeCortex

CodeCortex is a repository memory system for AI agents, extended with a deterministic execution substrate to enable reliable operation in multi-agent and OpenClaw-aligned environments.

It helps AI agents understand a repository, retain reusable project knowledge across sessions, and operate through a single reliable execution path.

## Product Definition

CodeCortex has two complementary responsibilities:

1. **Repository memory**
   - build and persist a structural and semantic understanding of the repository
   - provide compact retrieval commands for AI agents
   - store reusable semantic assertions and project decisions

2. **Deterministic execution substrate**
   - provide a controlled execution path for repository operations
   - align agent behavior across IDE and OpenClaw environments
   - support safe evolution toward multi-agent coordination

Repository memory remains the core identity of the project.
The execution substrate exists to make that memory reliable and usable in real agent workflows.

## Why CodeCortex Exists

AI coding agents often work like this:

```text
prompt → scan code → reason → respond
```

When a new session starts, the repository is explored again.
This wastes tokens, repeats reasoning, and increases the chance of missing important dependencies.

CodeCortex addresses this by turning a repository into a persistent local memory system.
Instead of repeatedly rediscovering structure, relationships, and validated project knowledge, agents can query and reuse what is already known.

As agent-driven development becomes more capable, repository memory alone is not enough.
Agents also need a reliable and deterministic way to operate on the repository, especially when multiple tools or agent environments interact with the same project.

That is why CodeCortex is evolving beyond repository understanding into a repository-aligned runtime model.

## Current Direction

CodeCortex is evolving toward the following architecture:

- **Codecortex core** understands repository structure and semantic relationships
- **Runtime layer** enforces a deterministic operational path
- **AI agents** decide what should happen
- **OpenClaw and IDE environments** invoke the same repo-local runtime boundary

Design principles:

- repository-local architecture
- single execution path
- clear separation between reasoning and execution
- deterministic behavior over implicit agent behavior
- extensibility toward coordinated multi-agent workflows

## Status

**Current status:** experimental project under active architectural transition.

What exists today:
- repository scanning and graph building
- repository-local memory under `.codecortex/`
- retrieval-oriented CLI commands
- semantic assertion storage
- feature-oriented graph slices
- benchmark utilities
- minimal repo-local runtime layer (v1)
- deterministic file operation path
- validation before mutation
- structured operation logging
- minimal write locking
- deterministic command execution path
- OpenClaw-aligned execution workflow
- test coverage for both graph/query behavior and execution v1

What evolves next:
- stronger CLI ergonomics
- broader user-facing examples and integration polish
- improved coordination beyond v1 minimal locking

## Core Concepts

### 1. Repository Memory

CodeCortex persists repository knowledge inside the project itself.

This memory layer is designed to store:
- structural dependencies
- symbol relationships
- semantic framework-specific relations
- feature-level slices
- reusable project decisions
- persistent semantic assertions

The goal is to reduce repeated exploration and repeated reasoning cost for AI agents.

### 2. Deterministic Execution Substrate

CodeCortex is also evolving a repo-local execution substrate.

This layer is intended to:
- enforce a single path for repository mutations
- prevent ad-hoc direct file changes by participating agents
- support safe file operations and validation
- provide a clean integration point for OpenClaw and IDE agents
- prepare for future multi-agent coordination

This is not intended to replace AI reasoning.
It exists to make execution predictable, debuggable, and reliable.

## Architecture Overview

```text
[ IDE Agent ]      [ OpenClaw Agent ]
       \              /
        \            /
         -> repo-local CLI -> runtime gateway -> CodeCortex
                              ├─ repository memory
                              └─ runtime + execution substrate
                                   ↓
                                repository
```

## Repository Layout

Current repository structure includes:

```text
codecortex/
  cli/
  codecortex/
  docs/
  tests/
```

Target runtime structure inside a project repository:

```text
repo/
  codecortex/
    core/
    execution/
    cli.py
  .codecortex/
    graph.json
    meta.json
    semantics.json
    semantics.journal.jsonl
    features.json
    constraints.json
    decisions.jsonl
    logs/
    locks/
```

## What CodeCortex Does Today

Today, CodeCortex can:

- parse Python repositories into a persistent graph of files, modules, classes, functions, and methods
- extract structural relationships such as `imports`, `defines`, `inherits`, `calls`, and `decorated_by`
- infer Django-specific relations such as `is_django_model`, `is_django_form`, `is_django_view`, `binds_model`, `uses_form`, `uses_model`, `uses_template`, and `delegates_to`
- return compact subgraphs with `query`, `symbol`, `impact`, and `context`
- persist semantic assertions in `.codecortex/semantics.json`
- rebuild semantic state from an append-only journal
- store feature-specific graph slices
- store lightweight project decisions
- benchmark retrieval payload size and approximate token cost

## What Comes Next

Near-term roadmap:

### v2 — improved coordination
- heartbeat-based lock renewal
- read/write lock separation
- better stale-lock handling
- retry strategies for blocked agents
- richer capability reporting for external agents and OpenClaw
- stronger CLI ergonomics for execution commands

### v3 — advanced coordination
- multi-resource operations
- rollback strategies
- operation state tracking
- conflict detection

### v4 — optional global capabilities
- selective shared intelligence
- optional cross-repo coordination
- stronger centralized governance only if justified

## Installation Modes

CodeCortex setup has two distinct levels:

1. **Environment-level install**
   - makes the `cortex` CLI available to an agent or runner environment
   - this is required before CodeCortex can be used anywhere

2. **Repository-level activation**
   - enables CodeCortex for a specific repository
   - creates repo-local memory and agent instructions
   - prepares the repository for CodeCortex-aware operation

These levels are intentionally separate.

Installing CodeCortex in the OpenClaw environment does **not** automatically enable it for every repository.
Each target repository must be activated explicitly.

## Mode 1 — Install CodeCortex in the agent environment

Use this when you want OpenClaw or another agent environment to have access to the `cortex` CLI.

### Prerequisites

- Python 3.9 or newer
- `pip`
- `git` recommended

### Example

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install CodeCortex from GitHub:

```bash
pip install 'git+https://github.com/costeamarius/codecortex.git'
```

Verify the CLI:

```bash
cortex --help
```

At this point, the environment is CodeCortex-capable, but no repository has been activated yet.

## Mode 2 — Activate CodeCortex in a repository

Use this when you want a specific repository to become CodeCortex-enabled.

Change into the target repository:

```bash
cd <repo>
```

Initialize repository storage:

```bash
cortex init .
```

Generate repository agent instructions:

```bash
cortex init-agent .
```

Build the initial graph:

```bash
cortex scan .
```

Confirm repository status:

```bash
cortex status .
```

This activates CodeCortex for the current repository.

Expected repo-local artifacts include:

- `.codecortex/`
- `AGENTS.md`

The authoritative enablement marker is a valid `.codecortex/meta.json`.
`AGENTS.md` and the presence of `.codecortex/` are advisory only.

## Mode 3 — OpenClaw-aware repository activation

When CodeCortex is used through OpenClaw, setup should follow a unified flow:

1. ensure `cortex` is available in the OpenClaw environment
2. determine the target repository path
3. activate CodeCortex in that repository if missing
4. query repository capabilities
5. switch into CodeCortex-aware repo mode

After repository activation, OpenClaw should query repo-local capabilities:

```bash
cortex capabilities --path .
```

OpenClaw should then use the repo-local CodeCortex contract for supported operations through `cortex action`.

## OpenClaw Quick Start

If you want to use CodeCortex through OpenClaw, give the following prompt to your OpenClaw agent.

### Copy-paste prompt for OpenClaw

```text
Set up CodeCortex for OpenClaw-aware use.

Install CodeCortex from GitHub:
https://github.com/costeamarius/codecortex

First, ensure CodeCortex is available in the OpenClaw environment.
Then determine the target repository path.
If the repository path is not explicit, ask me for it before continuing.

After the repository is known, detect whether CodeCortex is already activated there by checking for a valid `.codecortex/meta.json`.
If not, run the standard repository bootstrap:
- cortex init <repo>
- cortex init-agent <repo>
- cortex scan <repo>
- cortex status <repo>

Then run:
- cortex capabilities --path <repo>

Treat environment-level install and repository-level activation as separate steps.
Do not assume that installing CodeCortex for OpenClaw automatically enables it for every repository.
```

### What this prompt is for

This prompt is intended for users who want OpenClaw to:

1. install or verify CodeCortex in the OpenClaw environment
2. ask for the target repository if needed
3. activate CodeCortex in that specific repository
4. switch into CodeCortex-aware repo mode

The user-facing prompt above is intentionally short.
The full OpenClaw bootstrap and environment-detection flow is documented in:

- `docs/openclaw-bootstrap-flow.md`

## Environment Detection

Agents should distinguish between environment-level install and repository-level activation.

### Check 1 — Is CodeCortex available in this environment?

```bash
cortex --help
```

If this fails, CodeCortex is not installed in the current environment.

### Check 2 — Is the repository already CodeCortex-enabled?

A repository is CodeCortex-enabled only when `.codecortex/meta.json` exists and is valid.

`AGENTS.md`, `.codecortex/`, and other markers are advisory and may exist before activation is complete.

### Check 3 — If running in OpenClaw

OpenClaw should query:

```bash
cortex capabilities --path <repo>
```

and adopt the repository-defined operating model.

## Current CLI

The current CLI now exposes repository-memory commands plus the runtime boundary for supported mutations.

### Initialize repository storage

```bash
cortex init .
```

### Generate repository agent instructions

```bash
cortex init-agent .
```

### Build a full repository graph

```bash
cortex scan .
```

### Update graph incrementally

```bash
cortex update .
```

### Inspect graph status

```bash
cortex status .
```

### Query repository graph

```bash
cortex query moderation --type module
cortex symbol codecortex.graph_builder.build_graph --depth 1 --limit 12
cortex impact codecortex/graph_builder.py --depth 2 --limit 16
cortex context codecortex/graph_builder.py
```

### Persist semantic assertions

```bash
cortex semantics add featured_portfolio.photographer.form \
  function:fashion.portfolio.views.edit_featured_photographer \
  uses_form \
  class:fashion.portfolio.forms.PortfolioFormPhotographer \
  --source agent_inferred --confidence high

cortex semantics show --predicate uses_form
cortex semantics rebuild
```

### Work with feature slices

```bash
cortex feature build image_moderation --seed "moderation,images,delete_user,gdpr" --max-files 200
cortex feature show image_moderation
cortex feature refresh image_moderation
```

### Benchmark retrieval payloads

```bash
cortex benchmark query graph_builder --type function --limit 5
cortex benchmark symbol codecortex.graph_builder.build_graph --depth 1 --limit 12
cortex benchmark impact codecortex/graph_builder.py --depth 2 --limit 16
```

### Runtime commands

```bash
cortex capabilities --path .
cortex action --stdin
cortex action --request-file request.json
```

The legacy `edit-file` and `run-command` commands remain available, but the canonical machine-readable ingress for participating agents is `cortex action`.

## Expected Workflow

CodeCortex is used in two phases:

### Phase 1 — Prepare the environment

Make sure the current agent environment has the `cortex` CLI available.

```bash
cortex --help
```

If `cortex` is not available, install CodeCortex first.

### Phase 2 — Prepare the repository

For each target repository:

```bash
cortex init .
cortex init-agent .
cortex scan .
cortex status .
```

If operating through OpenClaw, also run:

```bash
cortex capabilities --path .
```

For supported mutations, submit structured JSON through:

```bash
cortex action --stdin
```

### Ongoing workflow

Once the repository is activated:

```bash
cortex status .
cortex query <term>
cortex context <file>
cortex symbol <qualified_symbol>
cortex impact <file_or_symbol>
```

When repository knowledge changes:

```bash
cortex update .
```

When validated semantic knowledge should be persisted:

```bash
cortex semantics add <assertion_id> <subject> <predicate> <object>
```

OpenClaw and IDE agents should follow the same repo-defined operating model once the repository is CodeCortex-enabled.

## OpenClaw Alignment

CodeCortex is designed to work cleanly with OpenClaw.

OpenClaw should act as:
- detector
- environment-level bootstrapper
- repository activator when needed
- runner
- result carrier

OpenClaw should not become the place where repository execution logic lives.
That logic belongs in the repo-local CodeCortex layer.

In practice, OpenClaw should:

1. ensure `cortex` is available in its environment
2. determine the target repository path
3. activate CodeCortex in that repository if needed
4. run `cortex capabilities --path <repo>`
5. use `cortex action` as the runtime ingress for supported operations

## Output Files (`.codecortex/`)

CodeCortex currently stores local repository memory in `.codecortex/`.

Artifacts may include:
- `graph.json`
- `meta.json`
- `semantics.json`
- `semantics.journal.jsonl`
- `features.json`
- `constraints.json`
- `decisions.jsonl`

Runtime artifacts include:
- `logs/`
- `locks/`
- `state.json`

## Git Policy

- `.codecortex/` is local repository memory and is ignored by default
- repository docs and ADRs are versioned
- user-facing documentation should be kept current with the real product state

## Documentation Policy

Project documentation is part of the product.

The following should be kept aligned with the actual implementation as development continues:
- `README.md`
- ADRs
- architecture docs
- CLI help text
- setup instructions
- user-facing examples

The goal is for repository documentation to always reflect the latest real product behavior and direction.

## Troubleshooting

- `cortex: command not found`
  - activate the virtual environment and rerun `pip install -e .`
- `Graph not found. Run 'cortex scan' first.`
  - run `cortex scan .` before retrieval commands
- `AGENTS.md already exists`
  - use `cortex init-agent . --force` only if you intend to replace it
- `update` falls back to full scan
  - ensure the target folder is a git repository and `git` is installed

## License

MIT
