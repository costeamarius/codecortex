from collections import deque


DEFAULT_NODE_FIELDS = (
    "id",
    "type",
    "name",
    "qualname",
    "path",
    "module",
    "line",
    "scope",
)

DEFAULT_EDGE_FIELDS = (
    "from",
    "to",
    "type",
    "line",
    "resolution",
    "origin",
    "assertion_id",
    "source",
)


def search_graph(graph, term, node_type=None, edge_type=None, limit=10):
    lowered_term = term.lower()
    nodes = graph.get("nodes", [])
    matches = []
    for node in nodes:
        if node_type and node.get("type") != node_type:
            continue
        if any(lowered_term in value for value in _node_search_values(node)):
            matches.append(_summarize_node(node))

    matches = sorted(matches, key=lambda node: node["id"])[:limit]
    matched_ids = {node["id"] for node in matches}
    relations = [
        _summarize_edge(edge)
        for edge in graph.get("edges", [])
        if (not edge_type or edge.get("type") == edge_type)
        and (edge.get("from") in matched_ids or edge.get("to") in matched_ids)
    ]
    relations = sorted(
        relations,
        key=lambda edge: (edge["type"], edge["from"], edge["to"], edge.get("line") or 0),
    )[: max(limit * 4, 20)]
    return {
        "term": term,
        "node_type": node_type,
        "edge_type": edge_type,
        "matches": matches,
        "relations": relations,
        "counts": {
            "matches": len(matches),
            "relations": len(relations),
        },
    }


def symbol_subgraph(graph, symbol, depth=1, edge_type=None, limit=25):
    node = _resolve_symbol(graph, symbol)
    if not node:
        return None
    return expand_subgraph(
        graph=graph,
        seed_ids=[node["id"]],
        depth=depth,
        edge_type=edge_type,
        limit=limit,
        label=symbol,
    )


def impact_subgraph(graph, target, depth=2, edge_type=None, limit=40):
    node = _resolve_file(graph, target)
    if not node:
        node = _resolve_symbol(graph, target)
    if not node:
        return None
    return expand_subgraph(
        graph=graph,
        seed_ids=[node["id"]],
        depth=depth,
        edge_type=edge_type,
        limit=limit,
        label=target,
    )


def expand_subgraph(graph, seed_ids, depth=1, edge_type=None, limit=25, label=None):
    nodes = graph.get("nodes", [])
    node_by_id = {node.get("id"): node for node in nodes if node.get("id")}
    edges = graph.get("edges", [])
    adjacent = {}
    for edge in edges:
        if edge_type and edge.get("type") != edge_type:
            continue
        source = edge.get("from")
        target = edge.get("to")
        if not source or not target:
            continue
        adjacent.setdefault(source, []).append((target, edge))
        adjacent.setdefault(target, []).append((source, edge))

    visited = set(seed_ids)
    distances = {seed_id: 0 for seed_id in seed_ids}
    queue = deque(seed_ids)
    collected_edges = []
    while queue:
        current = queue.popleft()
        current_depth = distances[current]
        if current_depth >= depth:
            continue
        for neighbor, edge in adjacent.get(current, []):
            collected_edges.append(edge)
            if neighbor in visited:
                continue
            visited.add(neighbor)
            distances[neighbor] = current_depth + 1
            queue.append(neighbor)
            if len(visited) >= limit:
                queue.clear()
                break

    selected_nodes = [
        _summarize_node(node_by_id[node_id])
        for node_id in sorted(visited)
        if node_id in node_by_id
    ]
    selected_edges = []
    selected_node_ids = {node["id"] for node in selected_nodes}
    seen_edges = set()
    for edge in collected_edges:
        edge_key = (
            edge.get("from"),
            edge.get("to"),
            edge.get("type"),
            edge.get("line"),
        )
        if edge_key in seen_edges:
            continue
        if edge.get("from") in selected_node_ids and edge.get("to") in selected_node_ids:
            selected_edges.append(_summarize_edge(edge))
            seen_edges.add(edge_key)

    selected_edges = sorted(
        selected_edges,
        key=lambda edge: (edge["type"], edge["from"], edge["to"], edge.get("line") or 0),
    )
    return {
        "label": label,
        "seed_ids": seed_ids,
        "depth": depth,
        "edge_type": edge_type,
        "nodes": selected_nodes,
        "relations": selected_edges,
        "counts": {
            "nodes": len(selected_nodes),
            "relations": len(selected_edges),
        },
    }


def _resolve_symbol(graph, symbol):
    exact_candidates = []
    fuzzy_candidates = []
    for node in graph.get("nodes", []):
        if node.get("type") not in {"class", "function", "method", "symbol"}:
            continue
        if symbol == node.get("id") or symbol == node.get("qualname"):
            exact_candidates.append(node)
        elif symbol == node.get("name"):
            exact_candidates.append(node)
        elif any(symbol.lower() in value for value in _node_search_values(node)):
            fuzzy_candidates.append(node)

    if len(exact_candidates) == 1:
        return exact_candidates[0]
    if exact_candidates:
        return sorted(exact_candidates, key=lambda node: node["id"])[0]
    if len(fuzzy_candidates) == 1:
        return fuzzy_candidates[0]
    if fuzzy_candidates:
        return sorted(fuzzy_candidates, key=lambda node: node["id"])[0]
    return None


def _resolve_file(graph, path_or_id):
    normalized = path_or_id.replace("\\", "/")
    file_id = normalized if normalized.startswith("file:") else f"file:{normalized}"
    for node in graph.get("nodes", []):
        if node.get("id") == file_id or node.get("path") == normalized:
            return node
    return None


def _node_search_values(node):
    return [
        str(node.get("id", "")).lower(),
        str(node.get("path", "")).lower(),
        str(node.get("name", "")).lower(),
        str(node.get("qualname", "")).lower(),
        str(node.get("module", "")).lower(),
    ]


def _summarize_node(node):
    return {
        key: node[key]
        for key in DEFAULT_NODE_FIELDS
        if key in node and node.get(key) is not None
    }


def _summarize_edge(edge):
    return {
        key: edge[key]
        for key in DEFAULT_EDGE_FIELDS
        if key in edge and edge.get(key) is not None
    }
