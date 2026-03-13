import os
import tempfile
import unittest

from codecortex.graph_query import impact_subgraph, search_graph
from codecortex.semantics_store import (
    append_jsonl,
    merge_graph_with_semantics,
    normalize_semantics_store,
    read_jsonl,
    rebuild_semantics_store_from_events,
    upsert_assertion,
)


class SemanticsStoreTests(unittest.TestCase):
    def test_merge_graph_with_semantics_adds_asserted_relations(self):
        graph = {
            "nodes": [
                {
                    "id": "function:app.views.edit_featured_photographer",
                    "type": "function",
                    "name": "edit_featured_photographer",
                    "qualname": "app.views.edit_featured_photographer",
                    "path": "app/views.py",
                    "module": "app.views",
                }
            ],
            "edges": [],
        }
        store = normalize_semantics_store(None)
        upsert_assertion(
            store,
            {
                "id": "featured.form",
                "subject": "function:app.views.edit_featured_photographer",
                "predicate": "uses_form",
                "object": "class:app.forms.PortfolioFormPhotographer",
                "source": "agent_inferred",
                "confidence": "high",
            },
        )

        merged = merge_graph_with_semantics(graph, store)
        payload = search_graph(merged, term="edit_featured_photographer", node_type="function", limit=10)

        self.assertEqual(1, payload["counts"]["matches"])
        self.assertEqual(1, payload["counts"]["relations"])
        relation = payload["relations"][0]
        self.assertEqual("uses_form", relation["type"])
        self.assertEqual("semantic_memory", relation["origin"])
        self.assertEqual("featured.form", relation["assertion_id"])

    def test_impact_subgraph_includes_asserted_nodes(self):
        graph = {
            "nodes": [
                {"id": "file:app/views.py", "type": "file", "path": "app/views.py"},
                {
                    "id": "function:app.views.edit_featured_photographer",
                    "type": "function",
                    "name": "edit_featured_photographer",
                    "qualname": "app.views.edit_featured_photographer",
                    "path": "app/views.py",
                    "module": "app.views",
                },
            ],
            "edges": [
                {"from": "file:app/views.py", "to": "function:app.views.edit_featured_photographer", "type": "defines"}
            ],
        }
        store = normalize_semantics_store(
            {
                "schema_version": "1.0",
                "assertions": [
                    {
                        "id": "featured.model",
                        "subject": "function:app.views.edit_featured_photographer",
                        "predicate": "uses_model",
                        "object": "class:app.models.PortfolioImagePhotographer",
                        "source": "user_confirmed",
                        "confidence": "high",
                    }
                ],
            }
        )

        merged = merge_graph_with_semantics(graph, store)
        payload = impact_subgraph(merged, target="app/views.py", depth=2, limit=10)

        self.assertIsNotNone(payload)
        node_ids = {node["id"] for node in payload["nodes"]}
        self.assertIn("class:app.models.PortfolioImagePhotographer", node_ids)
        self.assertTrue(
            any(relation.get("origin") == "semantic_memory" for relation in payload["relations"])
        )

    def test_rebuild_semantics_store_from_journal_preserves_multiple_assertions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = os.path.join(temp_dir, "semantics.journal.jsonl")
            append_jsonl(
                journal_path,
                {
                    "type": "upsert_assertion",
                    "assertion": {
                        "id": "featured.form",
                        "subject": "function:app.views.edit_featured_photographer",
                        "predicate": "uses_form",
                        "object": "class:app.forms.PortfolioFormPhotographer",
                    },
                },
            )
            append_jsonl(
                journal_path,
                {
                    "type": "upsert_assertion",
                    "assertion": {
                        "id": "featured.model",
                        "subject": "function:app.views.edit_featured_photographer",
                        "predicate": "uses_model",
                        "object": "class:app.models.PortfolioImagePhotographer",
                    },
                },
            )

            events = read_jsonl(journal_path)
            store = rebuild_semantics_store_from_events(events)

            self.assertEqual(2, len(store["assertions"]))
            assertion_ids = {assertion["id"] for assertion in store["assertions"]}
            self.assertEqual({"featured.form", "featured.model"}, assertion_ids)


if __name__ == "__main__":
    unittest.main()
