import os
import tempfile
import unittest

from codecortex.graph_builder import build_graph, update_graph


class IncrementalSymbolUpdateTests(unittest.TestCase):
    def test_update_graph_removes_stale_symbol_nodes(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, "pkg"), exist_ok=True)
            with open(os.path.join(repo_path, "pkg", "__init__.py"), "w", encoding="utf-8") as f:
                f.write("")
            target_path = os.path.join(repo_path, "pkg", "main.py")
            with open(target_path, "w", encoding="utf-8") as f:
                f.write("def old_name():\n    return 1\n")

            graph = build_graph(repo_path, generated_at="t1", git_commit="c1")

            with open(target_path, "w", encoding="utf-8") as f:
                f.write("def new_name():\n    return 2\n")

            updated = update_graph(
                existing_graph=graph,
                repo_path=repo_path,
                changed_files={"pkg/main.py"},
                generated_at="t2",
                git_commit="c2",
            )

            node_ids = {node["id"] for node in updated["nodes"]}
            self.assertIn("function:pkg.main.new_name", node_ids)
            self.assertNotIn("function:pkg.main.old_name", node_ids)


if __name__ == "__main__":
    unittest.main()
