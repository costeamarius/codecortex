import json

from codecortex.graph_query import impact_subgraph, search_graph, symbol_subgraph


def benchmark_query(graph, term, node_type=None, edge_type=None, limit=10):
    payload = search_graph(
        graph=graph,
        term=term,
        node_type=node_type,
        edge_type=edge_type,
        limit=limit,
    )
    return _with_stats("query", payload)


def benchmark_symbol(graph, symbol, depth=1, edge_type=None, limit=25):
    payload = symbol_subgraph(
        graph=graph,
        symbol=symbol,
        depth=depth,
        edge_type=edge_type,
        limit=limit,
    )
    if not payload:
        return None
    return _with_stats("symbol", payload)


def benchmark_impact(graph, target, depth=2, edge_type=None, limit=40):
    payload = impact_subgraph(
        graph=graph,
        target=target,
        depth=depth,
        edge_type=edge_type,
        limit=limit,
    )
    if not payload:
        return None
    return _with_stats("impact", payload)


def _with_stats(mode, payload):
    compact_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    node_type_counts = {}
    for node in payload.get("nodes", payload.get("matches", [])):
        node_type = node.get("type", "unknown")
        node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1

    edge_type_counts = {}
    for relation in payload.get("relations", []):
        edge_type = relation.get("type", "unknown")
        edge_type_counts[edge_type] = edge_type_counts.get(edge_type, 0) + 1

    return {
        "mode": mode,
        "summary": {
            "json_bytes": len(compact_json.encode("utf-8")),
            "json_chars": len(compact_json),
            "approx_tokens": _estimate_tokens(compact_json),
            "node_type_counts": dict(sorted(node_type_counts.items())),
            "edge_type_counts": dict(sorted(edge_type_counts.items())),
        },
        "payload": payload,
    }


def _estimate_tokens(text):
    if not text:
        return 0
    return max(1, round(len(text) / 4))
