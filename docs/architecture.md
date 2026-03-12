# CodeCortex Architecture

CodeCortex builds a persistent knowledge graph of a repository.

## Components

### Repo Scanner
Parses the repository using Python AST and extracts structural relationships.

### Dependency Graph
Creates a graph of modules, imports, and relationships.

### Semantic Feature Layer
Maps code elements to higher level features.

Example:

image_moderation  
├ moderation/services.py  
├ profiles/models.py  
└ delete_user_images.py

### Graph Storage

Stored in:

.codecortex/

Example files:

graph.json  
meta.json  
features.json  
constraints.json  
decisions.jsonl

`graph.json` schema (v1.1) includes:
- `schema_version`
- `generated_at`
- `git_commit`
- `nodes` (`file`, `module`)
- `edges` (`imports`) with provenance (`line`, `import_kind`, `relative_level`)

### Incremental Updates

CodeCortex reads git changes since the last scan commit and updates only affected nodes/edges.

CLI commands:
- `cortex init`
- `cortex scan`
- `cortex update`
- `cortex query`
- `cortex remember`
- `cortex feature build`
- `cortex feature show`
- `cortex feature refresh`

## Goal

Allow AI agents to query repository structure without rescanning the entire codebase.
