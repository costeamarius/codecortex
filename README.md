# CodeCortex

CodeCortex is an experimental open-source engine that turns a software repository into a persistent structural and semantic knowledge graph for AI agents.

AI coding tools repeatedly re-learn the same project structure every session.  
CodeCortex solves this by combining:
- a persistent structural and semantic graph extracted from code
- compact retrieval commands for AI agents
- a writable semantic memory layer for relationships discovered after analysis

## Problem

AI coding assistants currently work like this:

prompt → scan code → reason → response

When a new session starts, the repository must be analyzed again.  
This wastes tokens and increases the risk of missing architectural dependencies.

Example:

Feature: image moderation

Dependencies:
- user deletion
- GDPR export
- storage cleanup
- async tasks

If moderation logic changes, these relationships should be understood automatically.

## Solution

CodeCortex creates a persistent repository memory stored inside the repository.

The memory layer contains:

- structural dependencies
- symbol relationships
- framework-aware semantic relations
- feature relationships
- persisted semantic assertions
- architectural constraints

Instead of rescanning the project and re-deriving the same relationships every session, AI agents query and extend this memory layer.

## Architecture

repo  
↓  
cortex scan  
↓  
build project graph  
↓  
store graph in `.codecortex/`  
↓  
AI agents query relevant graph slices

## Goals

- persistent repository knowledge
- semantic feature mapping
- incremental graph updates from git diffs
- efficient AI context retrieval
- persistent semantic assertions that prevent repeated reasoning

## Status

Experimental prototype.

## Installation

### Prerequisites

- Python 3.9 or newer
- `pip`
- `git` (recommended for incremental updates via `cortex update`)

### Install

Create and activate a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate
```

Install as a local CLI tool:

```bash
pip install -e .
```

Then use:

```bash
cortex --help
```

## Quickstart (2 minutes)

From your repository root:

```bash
cortex init .
cortex init-agent .
cortex scan .
cortex status
cortex symbol codecortex.graph_builder.build_graph --depth 1 --limit 12
cortex benchmark impact codecortex/graph_builder.py --depth 2 --limit 16
cortex semantics show
```

You should now have a local `.codecortex/` folder with project memory artifacts.

## CLI (MVP)

Initialize repository storage:

```bash
python -m cli.cortex_cli init .
# or
cortex init .
```

Generate an `AGENTS.md` file for repository AI agent instructions:

```bash
python -m cli.cortex_cli init-agent .
# or
cortex init-agent .
```

Build full graph:

```bash
python -m cli.cortex_cli scan .
# or
cortex scan .
```

Incremental refresh from last scanned commit:

```bash
python -m cli.cortex_cli update .
# or
cortex update .
```

Inspect graph health and sync with current git commit:

```bash
python -m cli.cortex_cli status .
# or
cortex status .
```

Query graph nodes and relations:

```bash
python -m cli.cortex_cli query moderation --type module
# or
cortex query moderation --type module
```

Return dependency context for a specific file:

```bash
python -m cli.cortex_cli context codecortex/graph_builder.py
# or
cortex context codecortex/graph_builder.py
```

Persist short architecture decisions:

```bash
python -m cli.cortex_cli remember "Image Moderation Flow" "Moderation depends on delete-user cleanup and GDPR export."
# or
cortex remember "Image Moderation Flow" "Moderation depends on delete-user cleanup and GDPR export."
```

Retrieve a compact symbol-centered subgraph:

```bash
python -m cli.cortex_cli symbol codecortex.graph_builder.build_graph --depth 1 --limit 12
# or
cortex symbol codecortex.graph_builder.build_graph --depth 1 --limit 12
```

Retrieve a compact impact subgraph for a file or symbol:

```bash
python -m cli.cortex_cli impact codecortex/graph_builder.py --depth 2 --limit 16
# or
cortex impact codecortex/graph_builder.py --depth 2 --limit 16
```

Persist semantic assertions discovered by the agent or confirmed by the user:

```bash
python -m cli.cortex_cli semantics add featured_portfolio.photographer.form \
  function:fashion.portfolio.views.edit_featured_photographer \
  uses_form \
  class:fashion.portfolio.forms.PortfolioFormPhotographer \
  --source agent_inferred --confidence high
# or
cortex semantics add featured_portfolio.photographer.form \
  function:fashion.portfolio.views.edit_featured_photographer \
  uses_form \
  class:fashion.portfolio.forms.PortfolioFormPhotographer \
  --source agent_inferred --confidence high
```

Inspect stored semantic assertions:

```bash
python -m cli.cortex_cli semantics show --predicate uses_form
# or
cortex semantics show --predicate uses_form
```

Rebuild the materialized semantics store from the append-only journal:

```bash
python -m cli.cortex_cli semantics rebuild
# or
cortex semantics rebuild
```

Build a feature-specific graph slice on demand:

```bash
python -m cli.cortex_cli feature build image_moderation --seed "moderation,images,delete_user,gdpr" --max-files 200
# or
cortex feature build image_moderation --seed "moderation,images,delete_user,gdpr" --max-files 200
```

Inspect a stored feature slice:

```bash
python -m cli.cortex_cli feature show image_moderation
# or
cortex feature show image_moderation
```

Refresh an existing feature slice after code changes:

```bash
python -m cli.cortex_cli feature refresh image_moderation
# or
cortex feature refresh image_moderation
```

Benchmark retrieval payload size for a query:

```bash
python -m cli.cortex_cli benchmark query graph_builder --type function --limit 5
# or
cortex benchmark query graph_builder --type function --limit 5
```

Benchmark a symbol-centered subgraph:

```bash
python -m cli.cortex_cli benchmark symbol codecortex.graph_builder.build_graph --depth 1 --limit 12
# or
cortex benchmark symbol codecortex.graph_builder.build_graph --depth 1 --limit 12
```

Benchmark an impact subgraph for a file or symbol:

```bash
python -m cli.cortex_cli benchmark impact codecortex/graph_builder.py --depth 2 --limit 16
# or
cortex benchmark impact codecortex/graph_builder.py --depth 2 --limit 16
```

## Recommended Workflow

1. In each repository, initialize CodeCortex once:

```bash
python -m cli.cortex_cli init .
```

2. Generate repository instructions for AI agents:

```bash
python -m cli.cortex_cli init-agent .
```

3. Run a full scan when onboarding the project:

```bash
python -m cli.cortex_cli scan .
```

4. During day-to-day development, run incremental updates:

```bash
python -m cli.cortex_cli update .
```

5. Let AI agents query CodeCortex retrieval commands instead of rescanning the whole codebase:

```bash
python -m cli.cortex_cli query <term> --type module
python -m cli.cortex_cli symbol <qualified_symbol> --depth 1
python -m cli.cortex_cli impact <file_or_symbol> --depth 2
```

6. Check repository graph freshness before running AI-heavy tasks:

```bash
python -m cli.cortex_cli status .
```

7. Retrieve per-file dependency context for targeted edits:

```bash
python -m cli.cortex_cli context <file_path.py>
```

8. Store reusable, short architecture decisions:

```bash
python -m cli.cortex_cli remember "<title>" "<summary>"
```

9. Persist reusable semantic assertions once relationships are established:

```bash
python -m cli.cortex_cli semantics add <assertion_id> <subject> <predicate> <object>
python -m cli.cortex_cli semantics show
```

10. When working on a specific feature, build or refresh only that feature slice:

```bash
python -m cli.cortex_cli feature build <feature_name> --seed "<keywords>" --max-files 200
python -m cli.cortex_cli feature refresh <feature_name>
python -m cli.cortex_cli feature show <feature_name>
```

## Using With AI Agents

Installing CodeCortex is not enough by itself. The AI agent must also be instructed to use the `cortex` CLI.

The recommended setup is:

1. Install CodeCortex in the project environment.
2. Run `cortex init .`
3. Run `cortex init-agent .`
4. Run `cortex scan .`
5. Start the AI session from the repository root.

`cortex init-agent .` creates an `AGENTS.md` file in the repository root with instructions telling AI agents to:

- run `cortex status .` before manual repository exploration
- run `cortex scan .` if no graph exists
- run `cortex update .` if the graph is out of date
- use `cortex query <term>` for repository-wide discovery
- use `cortex context <file>` for file-level dependency context

If your AI tool supports `AGENTS.md`, it should load these instructions automatically when started in the repository.

In the current product shape, the highest-value workflow is:
- extract structure from code with `scan` / `update`
- retrieve compact subgraphs with `query`, `symbol`, and `impact`
- persist missing but validated relationships with `semantics add`
- reuse those persisted relations in later sessions without paying the reasoning cost again

If an `AGENTS.md` file already exists, `cortex init-agent .` will not overwrite it unless you pass `--force`.

## Output Files (`.codecortex/`)

After `init` and `scan`, CodeCortex stores:

- `.codecortex/graph.json`: graph nodes/edges and scan metadata
- `.codecortex/meta.json`: repository identity + last scan info
- `.codecortex/semantics.json`: persisted semantic assertions discovered or confirmed after analysis
- `.codecortex/semantics.journal.jsonl`: append-only event log used to rebuild `semantics.json`
- `.codecortex/features.json`: stored feature slices
- `.codecortex/constraints.json`: default architectural constraints
- `.codecortex/decisions.jsonl`: newline-delimited architecture decisions
- `AGENTS.md`: repository-level AI instructions generated by `cortex init-agent`

## Git Policy

- `.codecortex/` is local repository memory and is ignored by default.
- Recommended: run `python -m cli.cortex_cli update .` in CI (or hooks) so agent context stays fresh.

## What It Does Today

Today, CodeCortex can:

- parse Python repositories into a persistent graph of files, modules, classes, functions, and methods
- extract structural relationships such as `imports`, `defines`, `inherits`, `calls`, and `decorated_by`
- infer Django-specific relations such as `is_django_model`, `is_django_form`, `is_django_view`, `binds_model`, `uses_form`, `uses_model`, `uses_template`, and `delegates_to`
- return compact subgraphs with `query`, `symbol`, and `impact` for AI-friendly context retrieval
- benchmark retrieval payload size and approximate token cost
- persist semantic assertions in `.codecortex/semantics.json` so already-established relationships do not need to be re-derived in later sessions

This means CodeCortex is not just an indexer. It is a repository memory system that can both infer relationships from code and retain higher-level relationships once an agent or user has established them.

## Troubleshooting

- `cortex: command not found`
  - Ensure your virtual environment is active and rerun `pip install -e .`.
- `AGENTS.md already exists`
  - Run `cortex init-agent . --force` only if you want to overwrite the existing agent instructions.
- `Graph not found. Run 'cortex scan' first.`
  - Run `cortex scan .` before `status`, `query`, `context`, or `feature` commands.
- `update` falls back to full scan
  - Ensure the target folder is a git repository and `git` is installed.
- `File '<path>' is not present in the current graph.`
  - Run `cortex update .` (or `cortex scan .`) and retry `cortex context <path>`.

## License

MIT
