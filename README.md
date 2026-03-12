# CodeCortex

CodeCortex is an experimental open-source engine for building a persistent knowledge graph of a software repository.

AI coding tools repeatedly re-learn the same project structure every session.  
CodeCortex solves this by building a structural and semantic graph of the repository that evolves with the codebase.

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

CodeCortex creates a persistent project graph stored inside the repository.

The graph contains:

- structural dependencies
- feature relationships
- architectural constraints

Instead of rescanning the project, AI agents query the graph.

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
cortex scan .
cortex status
cortex query codecortex --type module
cortex context codecortex/graph_builder.py
```

You should now have a local `.codecortex/` folder with project memory artifacts.

## CLI (MVP)

Initialize repository storage:

```bash
python -m cli.cortex_cli init .
# or
cortex init .
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

## Recommended Workflow

1. In each repository, initialize CodeCortex once:

```bash
python -m cli.cortex_cli init .
```

2. Run a full scan when onboarding the project:

```bash
python -m cli.cortex_cli scan .
```

3. During day-to-day development, run incremental updates:

```bash
python -m cli.cortex_cli update .
```

4. Let AI agents query `.codecortex/graph.json` instead of rescanning the whole codebase:

```bash
python -m cli.cortex_cli query <term> --type module
```

5. Check repository graph freshness before running AI-heavy tasks:

```bash
python -m cli.cortex_cli status .
```

6. Retrieve per-file dependency context for targeted edits:

```bash
python -m cli.cortex_cli context <file_path.py>
```

7. Store reusable, short architecture decisions:

```bash
python -m cli.cortex_cli remember "<title>" "<summary>"
```

8. When working on a specific feature, build or refresh only that feature slice:

```bash
python -m cli.cortex_cli feature build <feature_name> --seed "<keywords>" --max-files 200
python -m cli.cortex_cli feature refresh <feature_name>
python -m cli.cortex_cli feature show <feature_name>
```

## Output Files (`.codecortex/`)

After `init` and `scan`, CodeCortex stores:

- `.codecortex/graph.json`: graph nodes/edges and scan metadata
- `.codecortex/meta.json`: repository identity + last scan info
- `.codecortex/features.json`: stored feature slices
- `.codecortex/constraints.json`: default architectural constraints
- `.codecortex/decisions.jsonl`: newline-delimited architecture decisions

## Git Policy

- `.codecortex/` is local repository memory and is ignored by default.
- Recommended: run `python -m cli.cortex_cli update .` in CI (or hooks) so agent context stays fresh.

## Troubleshooting

- `cortex: command not found`
  - Ensure your virtual environment is active and rerun `pip install -e .`.
- `Graph not found. Run 'cortex scan' first.`
  - Run `cortex scan .` before `status`, `query`, `context`, or `feature` commands.
- `update` falls back to full scan
  - Ensure the target folder is a git repository and `git` is installed.
- `File '<path>' is not present in the current graph.`
  - Run `cortex update .` (or `cortex scan .`) and retry `cortex context <path>`.

## License

MIT
