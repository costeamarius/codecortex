# CodeCortex Architecture

CodeCortex builds a persistent knowledge graph of a repository.

## Components

### Repo Scanner
Parses the repository using Python AST and extracts structural relationships.

Current extraction layers:
- file and module discovery
- import relationships
- Python symbol discovery (`class`, `function`, `method`)
- basic semantic relationships (`defines`, `inherits`, `calls`, `decorated_by`)
- Django semantic plugin for explicit framework relations

### Dependency Graph
Creates a graph of files, modules, symbols, and relationships.

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

`graph.json` schema (v1.2) includes:
- `schema_version`
- `generated_at`
- `git_commit`
- `nodes` (`file`, `module`, `class`, `function`, `method`, unresolved `symbol`)
- `edges`
  - `imports`
  - `defines`
  - `inherits`
  - `calls`
  - `decorated_by`
  - Django semantic edges such as `is_django_model`, `is_django_form`, `is_django_view`, `binds_model`, `uses_form`, `uses_model`, `uses_template`, `delegates_to`
- edge provenance:
  - `line`
  - `import_kind`
  - `relative_level`
  - `resolution`

### Incremental Updates

CodeCortex reads git changes since the last scan commit and updates only affected nodes/edges.

CLI commands:
- `cortex init`
- `cortex scan`
- `cortex update`
- `cortex query`
- `cortex symbol`
- `cortex impact`
- `cortex remember`
- `cortex feature build`
- `cortex feature show`
- `cortex feature refresh`

## Goal

Allow AI agents to query repository structure without rescanning the entire codebase.
