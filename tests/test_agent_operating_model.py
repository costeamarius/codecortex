import unittest

from codecortex.agent_operating_model import (
    direct_bypass_examples,
    get_agent_operating_model,
    is_participating_agent,
    required_codecortex_operations,
)


class AgentOperatingModelTests(unittest.TestCase):
    def test_known_environment_is_participating(self):
        self.assertTrue(is_participating_agent("openclaw"))
        self.assertTrue(is_participating_agent("cursor"))

    def test_unknown_environment_is_not_participating(self):
        self.assertFalse(is_participating_agent("unknown"))
        self.assertFalse(is_participating_agent(None))

    def test_required_operations_are_defined(self):
        operations = required_codecortex_operations()
        self.assertTrue(operations)
        self.assertIn("cortex edit-file", " ".join(operations))

    def test_bypass_examples_are_defined(self):
        examples = direct_bypass_examples()
        self.assertTrue(examples)
        self.assertIn("directly", examples[0])

    def test_operating_model_requires_repo_defined_behavior_for_participating_agents(self):
        payload = get_agent_operating_model("openclaw")
        self.assertTrue(payload["participating_agent"])
        self.assertTrue(payload["repo_defined_behavior_required"])
        self.assertTrue(payload["parity_expectation"]["ide_and_openclaw_should_match"])


if __name__ == "__main__":
    unittest.main()
