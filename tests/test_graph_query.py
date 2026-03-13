import unittest

from codecortex.graph_query import impact_subgraph, search_graph, symbol_subgraph


class GraphQueryTests(unittest.TestCase):
    def setUp(self):
        self.graph = {
            "nodes": [
                {"id": "file:pkg/main.py", "type": "file", "path": "pkg/main.py"},
                {
                    "id": "function:pkg.main.entry",
                    "type": "function",
                    "name": "entry",
                    "qualname": "pkg.main.entry",
                    "path": "pkg/main.py",
                    "module": "pkg.main",
                    "line": 1,
                },
                {
                    "id": "function:pkg.main.helper",
                    "type": "function",
                    "name": "helper",
                    "qualname": "pkg.main.helper",
                    "path": "pkg/main.py",
                    "module": "pkg.main",
                    "line": 4,
                },
                {
                    "id": "function:pkg.shared.work",
                    "type": "function",
                    "name": "work",
                    "qualname": "pkg.shared.work",
                    "path": "pkg/shared.py",
                    "module": "pkg.shared",
                    "line": 2,
                },
            ],
            "edges": [
                {"from": "file:pkg/main.py", "to": "function:pkg.main.entry", "type": "defines", "line": 1},
                {"from": "file:pkg/main.py", "to": "function:pkg.main.helper", "type": "defines", "line": 4},
                {
                    "from": "function:pkg.main.entry",
                    "to": "function:pkg.main.helper",
                    "type": "calls",
                    "line": 2,
                    "resolution": "local",
                },
                {
                    "from": "function:pkg.main.helper",
                    "to": "function:pkg.shared.work",
                    "type": "calls",
                    "line": 5,
                    "resolution": "imported",
                },
            ],
        }

    def test_search_graph_returns_compact_matches_and_relations(self):
        payload = search_graph(self.graph, term="pkg.main", node_type="function", limit=5)

        self.assertEqual(2, payload["counts"]["matches"])
        self.assertTrue(all("module" in node for node in payload["matches"]))
        self.assertTrue(all("import_kind" not in edge for edge in payload["relations"]))

    def test_symbol_subgraph_expands_from_symbol(self):
        payload = symbol_subgraph(self.graph, symbol="pkg.main.entry", depth=1, limit=10)

        self.assertIsNotNone(payload)
        node_ids = {node["id"] for node in payload["nodes"]}
        self.assertIn("function:pkg.main.entry", node_ids)
        self.assertIn("function:pkg.main.helper", node_ids)

    def test_impact_subgraph_resolves_file_targets(self):
        payload = impact_subgraph(self.graph, target="pkg/main.py", depth=2, limit=10)

        self.assertIsNotNone(payload)
        node_ids = {node["id"] for node in payload["nodes"]}
        self.assertIn("file:pkg/main.py", node_ids)
        self.assertIn("function:pkg.main.entry", node_ids)
        self.assertIn("function:pkg.shared.work", node_ids)


if __name__ == "__main__":
    unittest.main()
