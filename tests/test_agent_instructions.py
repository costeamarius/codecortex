import os
import tempfile
import unittest

from codecortex.agent_instructions import default_agents_md, write_agents_md


class AgentInstructionsTests(unittest.TestCase):
    def test_default_agents_md_points_agents_to_runtime_gateway(self):
        payload = default_agents_md()

        self.assertIn("cortex action", payload)
        self.assertIn("cortex action --stdin", payload)
        self.assertIn("structured JSON request envelope", payload)
        self.assertIn('"action": "edit_file|run_command"', payload)
        self.assertNotIn("cortex edit-file --path .", payload)
        self.assertNotIn("cortex run-command --path .", payload)

    def test_write_agents_md_writes_runtime_first_guidance(self):
        with tempfile.TemporaryDirectory() as repo_path:
            result = write_agents_md(repo_path, force=False)

            self.assertTrue(result["created"])
            agents_path = os.path.join(repo_path, "AGENTS.md")
            with open(agents_path, "r", encoding="utf-8") as handle:
                payload = handle.read()

            self.assertIn("Use the runtime gateway via `cortex action`", payload)
            self.assertIn("include `environment` and `agent_id`", payload)


if __name__ == "__main__":
    unittest.main()
