import re
from collections import deque


def normalize_features_store(payload):
    if not isinstance(payload, dict):
        return {"schema_version": "1.1", "features": []}
    features = payload.get("features")
    if not isinstance(features, list):
        features = []
    return {
        "schema_version": "1.1",
        "features": features,
    }


def get_feature(store, name):
    for feature in store.get("features", []):
        if feature.get("name") == name:
            return feature
    return None


def upsert_feature(store, feature):
    features = store.setdefault("features", [])
    for index, existing in enumerate(features):
        if existing.get("name") == feature.get("name"):
            features[index] = feature
            return
    features.append(feature)


def _name_tokens(feature_name):
    return [token for token in re.split(r"[^a-zA-Z0-9]+", feature_name.lower()) if token]


def _node_search_values(node):
    return [
        str(node.get("id", "")).lower(),
        str(node.get("path", "")).lower(),
        str(node.get("name", "")).lower(),
    ]


def _matches_any_term(node, terms):
    values = _node_search_values(node)
    return any(term in value for term in terms for value in values)


def _adjacency(edges):
    adjacent = {}
    for edge in edges:
        source = edge.get("from")
        target = edge.get("to")
        if not source or not target:
            continue
        adjacent.setdefault(source, set()).add(target)
        adjacent.setdefault(target, set()).add(source)
    return adjacent


def _collect_slice(seed_ids, adjacent):
    visited = set(seed_ids)
    queue = deque(seed_ids)
    while queue:
        node_id = queue.popleft()
        for neighbor in adjacent.get(node_id, []):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            queue.append(neighbor)
    return visited


def _related_features(existing_features, selected_files, current_name):
    related = []
    file_set = set(selected_files)
    for feature in existing_features:
        name = feature.get("name")
        if name == current_name:
            continue
        existing_files = set(feature.get("files", []))
        if file_set & existing_files:
            related.append(name)
    return sorted(related)


def build_feature_entry(
    graph,
    existing_features,
    name,
    seed_terms,
    max_files,
    timestamp,
    git_commit,
):
    normalized_terms = [term.strip().lower() for term in seed_terms if term.strip()]
    normalized_terms.extend(_name_tokens(name))
    normalized_terms = sorted(set(normalized_terms))

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_by_id = {node.get("id"): node for node in nodes if node.get("id")}

    seed_nodes = [
        node
        for node in nodes
        if normalized_terms and _matches_any_term(node, normalized_terms)
    ]
    if not seed_nodes:
        return None

    adjacent = _adjacency(edges)
    seed_ids = [node["id"] for node in seed_nodes]
    visited_ids = _collect_slice(seed_ids, adjacent)

    visited_files = []
    for node_id in visited_ids:
        node = node_by_id.get(node_id)
        if not node or node.get("type") != "file":
            continue
        path = node.get("path")
        if path:
            visited_files.append(path)
    selected_files = sorted(visited_files)[:max_files]
    selected_file_ids = {f"file:{path}" for path in selected_files}

    selected_module_ids = {
        edge["to"]
        for edge in edges
        if edge.get("from") in selected_file_ids and edge.get("to", "").startswith("module:")
    }
    selected_module_names = sorted(
        node_by_id[module_id].get("name")
        for module_id in selected_module_ids
        if module_id in node_by_id and node_by_id[module_id].get("name")
    )

    selected_nodes = sorted(selected_file_ids | selected_module_ids)
    selected_edges = [
        edge
        for edge in edges
        if edge.get("from") in selected_nodes and edge.get("to") in selected_nodes
    ]

    related = _related_features(existing_features, selected_files, name)

    return {
        "name": name,
        "seed_terms": normalized_terms,
        "max_files": max_files,
        "updated_at": timestamp,
        "git_commit": git_commit,
        "files": selected_files,
        "modules": selected_module_names,
        "relations": selected_edges,
        "related_features": related,
    }
