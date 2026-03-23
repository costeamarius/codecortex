# Usage Examples v1

- **Status:** Active
- **Date:** 2026-03-23

## Repository memory examples

### Initialize CodeCortex

```bash
cortex init .
```

### Build repository memory

```bash
cortex scan .
```

### Query existing repository knowledge

```bash
cortex query graph_builder --type function
cortex context codecortex/graph_builder.py
cortex symbol codecortex.graph_builder.build_graph --depth 1
cortex impact codecortex/graph_builder.py --depth 2
```

## Execution examples

### Inspect capabilities

```bash
cortex capabilities --path /repo
```

### Safe file edit

```bash
cortex edit-file \
  --path /repo \
  --file config.json \
  --content '{"timeout": 30}'
```

### Safe command execution

```bash
cortex run-command \
  --path /repo \
  --command 'python3 -m unittest -q'
```

## OpenClaw-aligned examples

### Detection and capability query

```bash
cortex capabilities --path /repo
```

### Repo-defined mutation path

```bash
cortex edit-file --path /repo --file settings.py --content 'DEBUG = False\n'
```

### Repo-defined command path

```bash
cortex run-command --path /repo --command 'python3 manage.py test'
```

## Codecortex-enabled repository behavior

If a repository is Codecortex-enabled, participating agents should:
- query CodeCortex first when practical
- use `cortex edit-file` for supported file edits
- use `cortex run-command` for supported command execution
- avoid direct bypass behavior for supported operations
