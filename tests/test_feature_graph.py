import unittest

from codecortex.feature_graph import build_feature_entry
from codecortex.semantics_store import merge_graph_with_semantics, normalize_semantics_store


class FeatureGraphTests(unittest.TestCase):
    def test_build_feature_entry_uses_merged_semantic_memory(self):
        graph = {
            "schema_version": "1.2",
            "generated_at": "t1",
            "git_commit": "c1",
            "nodes": [
                {"id": "file:app/views.py", "type": "file", "path": "app/views.py"},
                {
                    "id": "function:app.views.edit_feature",
                    "type": "function",
                    "name": "edit_feature",
                    "qualname": "app.views.edit_feature",
                    "path": "app/views.py",
                    "module": "app.views",
                },
                {"id": "file:app/forms.py", "type": "file", "path": "app/forms.py"},
                {
                    "id": "class:app.forms.FeatureForm",
                    "type": "class",
                    "name": "FeatureForm",
                    "qualname": "app.forms.FeatureForm",
                    "path": "app/forms.py",
                    "module": "app.forms",
                },
            ],
            "edges": [
                {"from": "file:app/views.py", "to": "function:app.views.edit_feature", "type": "defines"},
                {"from": "file:app/forms.py", "to": "class:app.forms.FeatureForm", "type": "defines"},
            ],
        }
        semantics = normalize_semantics_store(
            {
                "schema_version": "1.0",
                "assertions": [
                    {
                        "id": "feature.form",
                        "subject": "function:app.views.edit_feature",
                        "predicate": "uses_form",
                        "object": "class:app.forms.FeatureForm",
                        "source": "agent_inferred",
                        "confidence": "high",
                    }
                ],
            }
        )

        feature = build_feature_entry(
            graph=merge_graph_with_semantics(graph, semantics),
            existing_features=[],
            name="edit feature",
            seed_terms=[],
            max_files=10,
            timestamp="t2",
            git_commit="c2",
        )

        self.assertIsNotNone(feature)
        self.assertEqual(feature["files"], ["app/forms.py", "app/views.py"])
        relation_types = {relation["type"] for relation in feature["relations"]}
        self.assertIn("uses_form", relation_types)
        self.assertIn("app.forms", feature["modules"])
