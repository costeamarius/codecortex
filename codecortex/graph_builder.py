import json
import os
from .scanner import scan_python_files, extract_import_records


def _file_node_id(relative_path):
    return f"file:{relative_path}"


def _module_node_id(module_name):
    return f"module:{module_name}"


def _path_to_module(relative_path):
    normalized = relative_path.replace(os.sep, "/")
    if not normalized.endswith(".py"):
        return None
    module_path = normalized[:-3].replace("/", ".")
    if module_path.endswith(".__init__"):
        module_path = module_path[: -len(".__init__")]
    return module_path


def _resolve_import_module(source_module, record):
    module = record["module"]
    level = record["level"]

    if level == 0:
        return module

    source_parts = source_module.split(".") if source_module else []
    if level > len(source_parts):
        base_parts = []
    else:
        base_parts = source_parts[:-level]

    if module:
        return ".".join(base_parts + [module])

    return ".".join(base_parts)


def _is_internal_module(module_name, known_modules):
    if not module_name:
        return False
    if module_name in known_modules:
        return True
    return any(candidate.startswith(f"{module_name}.") for candidate in known_modules)


def _add_file_and_imports(nodes, edges, repo_path, relative_path, known_modules):
    file_path = os.path.join(repo_path, relative_path)
    if not os.path.exists(file_path):
        return

    file_node_id = _file_node_id(relative_path)
    nodes[file_node_id] = {
        "id": file_node_id,
        "type": "file",
        "path": relative_path,
    }

    source_module = _path_to_module(relative_path)
    import_records = extract_import_records(file_path)
    for record in import_records:
        resolved_module = _resolve_import_module(source_module, record)
        if not resolved_module:
            continue

        module_node_id = _module_node_id(resolved_module)
        nodes[module_node_id] = {
            "id": module_node_id,
            "type": "module",
            "name": resolved_module,
            "scope": "internal" if _is_internal_module(resolved_module, known_modules) else "external",
        }

        edges.add(
            (
                file_node_id,
                module_node_id,
                "imports",
                record["kind"],
                record["level"],
                record["lineno"],
            )
        )


def _finalize_graph(nodes, edges, generated_at, git_commit):
    return {
        "schema_version": "1.1",
        "generated_at": generated_at,
        "git_commit": git_commit,
        "nodes": sorted(nodes.values(), key=lambda node: node["id"]),
        "edges": [
            {
                "from": source,
                "to": target,
                "type": edge_type,
                "import_kind": import_kind,
                "relative_level": relative_level,
                "line": line_number,
            }
            for source, target, edge_type, import_kind, relative_level, line_number in sorted(edges)
        ],
    }


def _to_mutable_maps(graph):
    nodes = {node["id"]: node for node in graph.get("nodes", [])}
    edges = set()
    for edge in graph.get("edges", []):
        edges.add(
            (
                edge["from"],
                edge["to"],
                edge["type"],
                edge.get("import_kind"),
                edge.get("relative_level"),
                edge.get("line"),
            )
        )
    return nodes, edges


def _cleanup_graph(nodes, edges):
    valid_node_ids = set(nodes.keys())
    edges_to_keep = {
        edge for edge in edges if edge[0] in valid_node_ids and edge[1] in valid_node_ids
    }

    module_targets = {target for _, target, edge_type, _, _, _ in edges_to_keep if edge_type == "imports"}
    orphan_modules = [
        node_id
        for node_id, node in nodes.items()
        if node["type"] == "module" and node_id not in module_targets
    ]
    for orphan_id in orphan_modules:
        nodes.pop(orphan_id, None)

    valid_node_ids = set(nodes.keys())
    edges_to_keep = {
        edge for edge in edges_to_keep if edge[0] in valid_node_ids and edge[1] in valid_node_ids
    }
    return nodes, edges_to_keep


def _discover_python_files(repo_path):
    files = scan_python_files(repo_path)
    relative_paths = sorted(os.path.relpath(path, repo_path) for path in files)
    known_modules = {
        module_name
        for module_name in (_path_to_module(path) for path in relative_paths)
        if module_name
    }
    return relative_paths, known_modules


def build_graph(repo_path, generated_at=None, git_commit=None):
    relative_paths, known_modules = _discover_python_files(repo_path)
    nodes = {}
    edges = set()

    for relative_path in relative_paths:
        _add_file_and_imports(nodes, edges, repo_path, relative_path, known_modules)

    return _finalize_graph(nodes, edges, generated_at, git_commit)


def update_graph(existing_graph, repo_path, changed_files, generated_at=None, git_commit=None):
    if not changed_files:
        return build_graph(repo_path, generated_at=generated_at, git_commit=git_commit)

    nodes, edges = _to_mutable_maps(existing_graph)
    _, known_modules = _discover_python_files(repo_path)

    for relative_path in sorted(changed_files):
        if not relative_path.endswith(".py"):
            continue

        file_node_id = _file_node_id(relative_path)
        nodes.pop(file_node_id, None)
        edges = {edge for edge in edges if edge[0] != file_node_id}

        _add_file_and_imports(nodes, edges, repo_path, relative_path, known_modules)

    nodes, edges = _cleanup_graph(nodes, edges)
    return _finalize_graph(nodes, edges, generated_at, git_commit)


def save_graph(graph, repo_path):
    cortex_dir = os.path.join(repo_path, ".codecortex")
    os.makedirs(cortex_dir, exist_ok=True)

    graph_path = os.path.join(cortex_dir, "graph.json")

    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)
