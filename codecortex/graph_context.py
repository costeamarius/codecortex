import os

from codecortex.project_context import read_json
from codecortex.semantics_store import (
    merge_graph_with_semantics,
    normalize_semantics_store,
    read_jsonl,
    rebuild_semantics_store_from_events,
)


def _normalize_file_path(repo_path, file_path):
    if os.path.isabs(file_path):
        try:
            relative = os.path.relpath(file_path, repo_path)
        except ValueError:
            relative = file_path
    else:
        relative = file_path

    return relative.replace(os.sep, "/")


def _path_to_module(relative_path):
    normalized = relative_path.replace(os.sep, "/")
    if not normalized.endswith(".py"):
        return None

    module_path = normalized[:-3].replace("/", ".")
    if module_path.endswith(".__init__"):
        module_path = module_path[: -len(".__init__")]
    return module_path


def compute_file_context_from_graph(repo_path, graph, file_path):
    if not graph:
        return {"graph_present": False}

    normalized_file = _normalize_file_path(repo_path, file_path)
    file_node_id = f"file:{normalized_file}"
    nodes = graph.get("nodes", [])
    node_by_id = {node.get("id"): node for node in nodes if node.get("id")}
    if file_node_id not in node_by_id:
        return {
            "graph_present": True,
            "file_found": False,
            "file": normalized_file,
        }

    edges = graph.get("edges", [])
    imports = sorted(
        {
            edge.get("to")
            for edge in edges
            if edge.get("from") == file_node_id
            and edge.get("type") == "imports"
            and str(edge.get("to", "")).startswith("module:")
        }
    )

    module_name = _path_to_module(normalized_file)
    module_node_id = f"module:{module_name}" if module_name else None
    imported_by = []
    if module_node_id:
        imported_by = sorted(
            {
                edge.get("from")
                for edge in edges
                if edge.get("to") == module_node_id
                and edge.get("type") == "imports"
                and str(edge.get("from", "")).startswith("file:")
                and edge.get("from") != file_node_id
            }
        )

    defined_symbol_ids = sorted(
        {
            edge.get("to")
            for edge in edges
            if edge.get("from") == file_node_id and edge.get("type") == "defines"
        }
    )
    symbols_defined = [
        node_by_id[symbol_id]
        for symbol_id in defined_symbol_ids
        if symbol_id in node_by_id
    ]
    symbol_id_set = set(defined_symbol_ids)
    symbol_relations = [
        edge
        for edge in edges
        if edge.get("type") != "imports"
        and (
            edge.get("from") in symbol_id_set
            or edge.get("to") in symbol_id_set
        )
    ]

    return {
        "graph_present": True,
        "file_found": True,
        "file": normalized_file,
        "file_node": node_by_id[file_node_id],
        "file_node_id": file_node_id,
        "module_name": module_name,
        "module_node_id": module_node_id,
        "imports": imports,
        "imported_by": imported_by,
        "symbols_defined": symbols_defined,
        "symbol_relations": symbol_relations,
        "graph_metadata": {
            "schema_version": graph.get("schema_version"),
            "generated_at": graph.get("generated_at"),
            "git_commit": graph.get("git_commit"),
        },
    }


def compute_file_context(repo_path, graph_path, file_path):
    graph = read_json(graph_path)
    if graph:
        graph = _merge_graph_with_adjacent_semantic_memory(graph_path, graph)
    return compute_file_context_from_graph(repo_path, graph, file_path)


def _merge_graph_with_adjacent_semantic_memory(graph_path, graph):
    graph_dir = os.path.dirname(graph_path)
    semantics_path = os.path.join(graph_dir, "semantics.json")
    semantics_journal_path = os.path.join(graph_dir, "semantics.journal.jsonl")

    store = normalize_semantics_store(read_json(semantics_path))
    journal_events = read_jsonl(semantics_journal_path)
    if journal_events:
        rebuilt_store = rebuild_semantics_store_from_events(journal_events)
        if rebuilt_store.get("assertions") != store.get("assertions"):
            store = rebuilt_store

    if not store.get("assertions"):
        return graph
    return merge_graph_with_semantics(graph, store)
