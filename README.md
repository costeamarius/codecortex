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
codecortex scan  
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

## License

MIT