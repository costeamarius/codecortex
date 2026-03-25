import unittest

from codecortex.memory.constraint_store import (
    build_default_constraints,
    normalize_constraints_store,
    validate_constraints_store,
)


class ConstraintStoreTests(unittest.TestCase):
    def test_build_default_constraints_returns_structured_schema(self):
        payload = build_default_constraints()

        self.assertEqual(payload["schema_version"], "1.0")
        self.assertFalse(payload["require_fresh_graph"])
        self.assertEqual(payload["path_write_rules"][0]["mode"], "deny")
        self.assertEqual(payload["path_write_rules"][0]["pattern"], "docs/**")
        self.assertEqual(payload["command_rules"], [])
        self.assertTrue(payload["constraints"])

    def test_normalize_constraints_store_preserves_supported_rule_types(self):
        payload = normalize_constraints_store(
            {
                "schema_version": "1.1",
                "require_fresh_graph": True,
                "path_write_rule": {"mode": "deny", "pattern": "docs/**", "reason": "no docs writes"},
                "path_write_rules": [{"mode": "allow", "pattern": ".codecortex/**"}],
                "command_rule": {"type": "deny_program", "program": "rm"},
                "command_rules": [{"type": "deny_family", "family_name": "shell"}],
                "constraints": ["legacy note", 1],
            }
        )

        self.assertEqual(payload["schema_version"], "1.1")
        self.assertTrue(payload["require_fresh_graph"])
        self.assertEqual(
            payload["path_write_rules"],
            [
                {"mode": "deny", "pattern": "docs/**", "reason": "no docs writes"},
                {"mode": "allow", "pattern": ".codecortex/**"},
            ],
        )
        self.assertEqual(
            payload["command_rules"],
            [
                {"type": "deny_program", "program": "rm"},
                {"type": "deny_family", "family_name": "shell"},
            ],
        )
        self.assertEqual(payload["constraints"], ["legacy note"])

    def test_normalize_constraints_store_drops_invalid_rules(self):
        payload = normalize_constraints_store(
            {
                "path_write_rule": {"mode": "deny"},
                "path_write_rules": [{"mode": "bad", "pattern": "docs/**"}],
                "command_rule": {"type": "deny_program"},
                "command_rules": [{"type": "unknown", "program": "rm"}],
            }
        )

        self.assertEqual(payload["path_write_rules"], [])
        self.assertEqual(payload["command_rules"], [])

    def test_normalize_constraints_store_uses_defaults_for_missing_payload(self):
        payload = normalize_constraints_store(None)

        self.assertEqual(payload, build_default_constraints())

    def test_validate_constraints_store_reports_invalid_shapes(self):
        issues = validate_constraints_store(
            {
                "path_write_rules": "bad",
                "command_rule": {"type": "deny_program"},
                "constraints": "bad",
            }
        )

        self.assertIn("path_write_rules must be a list", issues)
        self.assertIn("command_rule is invalid", issues)
        self.assertIn("constraints must be a list", issues)


if __name__ == "__main__":
    unittest.main()
