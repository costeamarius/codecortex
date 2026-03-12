import os

from codecortex.project_context import read_json


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


def compute_file_context(repo_path, graph_path, file_path):
    graph = read_json(graph_path)
    if not graph:
        return {"graph_present": False}

    normalized_file = _normalize_file_path(repo_path, file_path)
    file_node_id = f"file:{normalized_file}"
    nodes = graph.get("nodes", [])
    node_ids = {node.get("id") for node in nodes}
    if file_node_id not in node_ids:
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

    return {
        "graph_present": True,
        "file_found": True,
        "file": normalized_file,
        "imports": imports,
        "imported_by": imported_by,
        "graph_metadata": {
            "schema_version": graph.get("schema_version"),
            "generated_at": graph.get("generated_at"),
            "git_commit": graph.get("git_commit"),
        },
    }
