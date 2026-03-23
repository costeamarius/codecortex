import os
import tempfile
import unittest

from codecortex.openclaw_integration import (
    detect_codecortex_enabled,
    get_openclaw_bootstrap_steps,
    get_openclaw_integration_payload,
)


class OpenClawIntegrationTests(unittest.TestCase):
    def test_detect_codecortex_enabled_by_runtime_dir(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex"), exist_ok=True)
            payload = detect_codecortex_enabled(repo_path)
            self.assertTrue(payload["codecortex_enabled"])
            self.assertTrue(payload["markers"]["runtime_dir"])

    def test_detect_codecortex_enabled_by_codecortex_dir(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, "codecortex"), exist_ok=True)
            payload = detect_codecortex_enabled(repo_path)
            self.assertTrue(payload["codecortex_enabled"])
            self.assertTrue(payload["markers"]["codecortex_dir"])

    def test_openclaw_integration_payload_exposes_runner_rules(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, "codecortex"), exist_ok=True)
            payload = get_openclaw_integration_payload(repo_path)
            self.assertTrue(payload["openclaw"]["must_use_repo_local_cli"])
            self.assertTrue(payload["openclaw"]["must_not_embed_execution_logic"])
            self.assertTrue(payload["openclaw"]["must_follow_repo_defined_behavior"])
            self.assertIn("capabilities", payload["openclaw"]["expected_commands"])

    def test_openclaw_bootstrap_steps_are_defined(self):
        payload = get_openclaw_bootstrap_steps()
        self.assertTrue(payload["steps"])
        self.assertIn("bootstrap Codecortex", " ".join(payload["steps"]))


if __name__ == "__main__":
    unittest.main()
