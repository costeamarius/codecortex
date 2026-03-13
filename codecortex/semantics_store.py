import json
import os


def normalize_semantics_store(payload):
    if not isinstance(payload, dict):
        return {"schema_version": "1.0", "assertions": []}
    assertions = payload.get("assertions")
    if not isinstance(assertions, list):
        assertions = []
    return {
        "schema_version": payload.get("schema_version") or "1.0",
        "assertions": assertions,
    }


def upsert_assertion(store, assertion):
    assertions = store.setdefault("assertions", [])
    assertion_id = assertion.get("id")
    if assertion_id:
        for index, existing in enumerate(assertions):
            if existing.get("id") == assertion_id:
                assertions[index] = assertion
                return
    assertions.append(assertion)


def rebuild_semantics_store_from_events(events):
    store = {"schema_version": "1.0", "assertions": []}
    for event in events:
        if not isinstance(event, dict):
            continue
        assertion = event.get("assertion") if event.get("type") == "upsert_assertion" else None
        if not assertion:
            continue
        upsert_assertion(store, assertion)
    return store


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def append_jsonl(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")


def get_assertions(store, subject=None, predicate=None, object_id=None):
    results = []
    for assertion in store.get("assertions", []):
        if subject and assertion.get("subject") != subject:
            continue
        if predicate and assertion.get("predicate") != predicate:
            continue
        if object_id and assertion.get("object") != object_id:
            continue
        results.append(assertion)
    return results


def merge_graph_with_semantics(graph, store):
    merged_nodes = {node["id"]: dict(node) for node in graph.get("nodes", []) if node.get("id")}
    merged_edges = [dict(edge) for edge in graph.get("edges", [])]

    for assertion in store.get("assertions", []):
        subject_id = assertion.get("subject")
        object_id = assertion.get("object")
        predicate = assertion.get("predicate")
        if not subject_id or not object_id or not predicate:
            continue

        if subject_id not in merged_nodes:
            merged_nodes[subject_id] = _node_from_id(subject_id)
        if object_id not in merged_nodes:
            merged_nodes[object_id] = _node_from_id(object_id)

        merged_edges.append(
            {
                "from": subject_id,
                "to": object_id,
                "type": predicate,
                "line": assertion.get("line"),
                "resolution": assertion.get("confidence") or "asserted",
                "origin": "semantic_memory",
                "assertion_id": assertion.get("id"),
                "source": assertion.get("source"),
            }
        )

    return {
        "schema_version": graph.get("schema_version"),
        "generated_at": graph.get("generated_at"),
        "git_commit": graph.get("git_commit"),
        "nodes": sorted(merged_nodes.values(), key=lambda node: node["id"]),
        "edges": merged_edges,
    }


def _node_from_id(node_id):
    prefix, _, rest = node_id.partition(":")
    if not rest:
        return {"id": node_id, "type": "symbol", "name": node_id}

    node_type = prefix
    name = rest.split(".")[-1].split("/")[-1]
    node = {
        "id": node_id,
        "type": node_type if node_type not in {"template", "semantic"} else node_type,
        "name": name,
    }
    if node_type in {"class", "function", "method", "symbol"}:
        node["qualname"] = rest
    if node_type == "file":
        node["path"] = rest
    if node_type == "module":
        node["name"] = rest
        node["scope"] = "unknown"
    if node_type == "template":
        node["path"] = rest
        node["name"] = rest.split("/")[-1]
    if node_type == "semantic":
        node["name"] = rest
    return node
