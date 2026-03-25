import json
import os
import tempfile
import unittest

from codecortex.graph_builder import build_graph
from codecortex.graph_context import compute_file_context


class SymbolGraphTests(unittest.TestCase):
    def test_build_graph_extracts_symbols_and_relations(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, "pkg"), exist_ok=True)
            with open(os.path.join(repo_path, "pkg", "__init__.py"), "w", encoding="utf-8") as f:
                f.write("")
            with open(os.path.join(repo_path, "pkg", "helpers.py"), "w", encoding="utf-8") as f:
                f.write("def external_helper():\n    return 1\n")
            with open(os.path.join(repo_path, "pkg", "main.py"), "w", encoding="utf-8") as f:
                f.write(
                    "from pkg.helpers import external_helper\n"
                    "\n"
                    "def helper():\n"
                    "    return external_helper()\n"
                    "\n"
                    "class Greeter(BaseGreeter):\n"
                    "    def greet(self):\n"
                    "        return helper()\n"
                )

            graph = build_graph(repo_path, generated_at="now", git_commit="head")
            node_ids = {node["id"] for node in graph["nodes"]}
            edges = {
                (edge["from"], edge["to"], edge["type"])
                for edge in graph["edges"]
            }

            self.assertIn("function:pkg.main.helper", node_ids)
            self.assertIn("class:pkg.main.Greeter", node_ids)
            self.assertIn("method:pkg.main.Greeter.greet", node_ids)
            self.assertIn(("file:pkg/main.py", "function:pkg.main.helper", "defines"), edges)
            self.assertIn(("class:pkg.main.Greeter", "method:pkg.main.Greeter.greet", "defines"), edges)
            self.assertIn(
                ("function:pkg.main.helper", "function:pkg.helpers.external_helper", "calls"),
                edges,
            )
            self.assertIn(
                ("method:pkg.main.Greeter.greet", "function:pkg.main.helper", "calls"),
                edges,
            )
            self.assertIn(
                ("class:pkg.main.Greeter", "symbol:pkg.main.BaseGreeter", "inherits"),
                edges,
            )

    def test_file_context_includes_defined_symbols(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, "pkg"), exist_ok=True)
            with open(os.path.join(repo_path, "pkg", "__init__.py"), "w", encoding="utf-8") as f:
                f.write("")
            with open(os.path.join(repo_path, "pkg", "main.py"), "w", encoding="utf-8") as f:
                f.write(
                    "def helper():\n"
                    "    return 1\n"
                    "\n"
                    "class Greeter:\n"
                    "    def greet(self):\n"
                    "        return helper()\n"
                )

            graph = build_graph(repo_path, generated_at="now", git_commit="head")
            graph_path = os.path.join(repo_path, "graph.json")
            with open(graph_path, "w", encoding="utf-8") as f:
                json.dump(graph, f)

            payload = compute_file_context(repo_path, graph_path, "pkg/main.py")
            symbol_ids = {symbol["id"] for symbol in payload["symbols_defined"]}

            self.assertTrue(payload["file_found"])
            self.assertIn("function:pkg.main.helper", symbol_ids)
            self.assertIn("class:pkg.main.Greeter", symbol_ids)

    def test_file_context_merges_adjacent_semantic_memory(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex"), exist_ok=True)
            os.makedirs(os.path.join(repo_path, "pkg"), exist_ok=True)
            with open(os.path.join(repo_path, "pkg", "__init__.py"), "w", encoding="utf-8") as f:
                f.write("")
            with open(os.path.join(repo_path, "pkg", "main.py"), "w", encoding="utf-8") as f:
                f.write("def helper():\n    return 1\n")

            graph = build_graph(repo_path, generated_at="now", git_commit="head")
            graph_path = os.path.join(repo_path, ".codecortex", "graph.json")
            with open(graph_path, "w", encoding="utf-8") as f:
                json.dump(graph, f)
            with open(os.path.join(repo_path, ".codecortex", "semantics.json"), "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "schema_version": "1.0",
                        "assertions": [
                            {
                                "id": "helper.rule",
                                "subject": "function:pkg.main.helper",
                                "predicate": "uses_rule",
                                "object": "semantic:repo.rule",
                            }
                        ],
                    },
                    f,
                )

            payload = compute_file_context(repo_path, graph_path, "pkg/main.py")
            relation_types = {relation["type"] for relation in payload["symbol_relations"]}

            self.assertIn("uses_rule", relation_types)


if __name__ == "__main__":
    unittest.main()
