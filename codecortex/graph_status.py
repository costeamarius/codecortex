from codecortex.project_context import get_head_commit, read_json


def compute_graph_status(repo_path, graph_path, meta_path):
    graph = read_json(graph_path)
    if not graph:
        return {
            "graph_present": False,
        }

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    files_count = sum(1 for node in nodes if node.get("type") == "file")
    modules_count = sum(1 for node in nodes if node.get("type") == "module")
    classes_count = sum(1 for node in nodes if node.get("type") == "class")
    functions_count = sum(1 for node in nodes if node.get("type") == "function")
    methods_count = sum(1 for node in nodes if node.get("type") == "method")

    meta = read_json(meta_path) or {}
    last_scan_at = meta.get("last_scan_at") or graph.get("generated_at")
    last_scan_commit = meta.get("last_scan_commit") or graph.get("git_commit")
    current_commit = get_head_commit(repo_path)

    if last_scan_commit and current_commit:
        sync_status = "up to date" if last_scan_commit == current_commit else "out of date"
    else:
        sync_status = "unknown"

    return {
        "graph_present": True,
        "nodes_count": len(nodes),
        "edges_count": len(edges),
        "files_count": files_count,
        "modules_count": modules_count,
        "classes_count": classes_count,
        "functions_count": functions_count,
        "methods_count": methods_count,
        "last_scan_at": last_scan_at,
        "last_scan_commit": last_scan_commit,
        "current_commit": current_commit,
        "sync_status": sync_status,
    }
