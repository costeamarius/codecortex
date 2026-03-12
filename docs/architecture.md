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
features.yaml  
constraints.yaml

### Incremental Updates

CodeCortex monitors git changes and updates only the affected nodes in the graph.

## Goal

Allow AI agents to query repository structure without rescanning the entire codebase.