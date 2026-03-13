import unittest

from codecortex.benchmarking import benchmark_impact, benchmark_query, benchmark_symbol


class BenchmarkingTests(unittest.TestCase):
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
                    "line": 3,
                },
            ],
            "edges": [
                {"from": "file:pkg/main.py", "to": "function:pkg.main.entry", "type": "defines", "line": 1},
                {
                    "from": "function:pkg.main.entry",
                    "to": "function:pkg.main.helper",
                    "type": "calls",
                    "line": 2,
                    "resolution": "local",
                },
            ],
        }

    def test_benchmark_query_reports_payload_size(self):
        payload = benchmark_query(self.graph, term="entry", node_type="function", limit=5)

        self.assertEqual("query", payload["mode"])
        self.assertGreater(payload["summary"]["json_bytes"], 0)
        self.assertGreater(payload["summary"]["approx_tokens"], 0)
        self.assertEqual(1, payload["summary"]["node_type_counts"]["function"])

    def test_benchmark_symbol_reports_compact_stats(self):
        payload = benchmark_symbol(self.graph, symbol="pkg.main.entry", depth=1, limit=10)

        self.assertEqual("symbol", payload["mode"])
        self.assertIn("calls", payload["summary"]["edge_type_counts"])

    def test_benchmark_impact_handles_files(self):
        payload = benchmark_impact(self.graph, target="pkg/main.py", depth=2, limit=10)

        self.assertEqual("impact", payload["mode"])
        self.assertIn("file", payload["summary"]["node_type_counts"])


if __name__ == "__main__":
    unittest.main()
