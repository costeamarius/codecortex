import json
import os
import tempfile
import unittest

from codecortex.memory.decision_store import append_decision, list_decisions, query_decisions


class DecisionStoreTests(unittest.TestCase):
    def test_append_and_list_decisions_normalizes_entries(self):
        with tempfile.TemporaryDirectory() as repo_path:
            decisions_path = os.path.join(repo_path, ".codecortex", "decisions.jsonl")
            entry = append_decision(
                decisions_path,
                {
                    "id": "decision-1",
                    "title": "Use runtime kernel",
                    "summary": "All actions should flow through the runtime.",
                    "tags": "runtime",
                },
            )

            self.assertEqual(entry["tags"], [])
            self.assertEqual(entry["references"], [])

            decisions = list_decisions(decisions_path)
            self.assertEqual([decision["id"] for decision in decisions], ["decision-1"])

            with open(decisions_path, "r", encoding="utf-8") as handle:
                stored = json.loads(handle.readline())
            self.assertEqual(stored["id"], "decision-1")
            self.assertEqual(stored["references"], [])

    def test_query_decisions_filters_by_targets(self):
        with tempfile.TemporaryDirectory() as repo_path:
            decisions_path = os.path.join(repo_path, ".codecortex", "decisions.jsonl")
            append_decision(
                decisions_path,
                {
                    "id": "decision-1",
                    "title": "Module rule",
                    "summary": "Keep pkg.module stable.",
                    "scope": "pkg.module",
                    "references": ["pkg/module.py"],
                },
            )
            append_decision(
                decisions_path,
                {
                    "id": "decision-2",
                    "title": "Repo note",
                    "summary": "General repo-wide note.",
                    "scope": "repo",
                },
            )

            matched = query_decisions(
                decisions_path,
                {"pkg.module", "pkg/module.py", "file:pkg/module.py"},
            )

            self.assertEqual([decision["id"] for decision in matched], ["decision-1"])
