import json
import os
import tempfile
import unittest

from codecortex.memory.detection import detect_repo_binding


class MemoryDetectionTests(unittest.TestCase):
    def test_repo_with_only_agents_md_is_not_enabled(self):
        with tempfile.TemporaryDirectory() as repo_path:
            with open(os.path.join(repo_path, "AGENTS.md"), "w", encoding="utf-8") as handle:
                handle.write("# Agents\n")

            binding = detect_repo_binding(repo_path)

            self.assertFalse(binding.enabled)
            self.assertEqual(binding.repo_root, repo_path)
            self.assertTrue(binding.markers["agents_md"])

    def test_repo_with_only_runtime_dir_is_not_enabled(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex"), exist_ok=True)

            binding = detect_repo_binding(repo_path)

            self.assertFalse(binding.enabled)
            self.assertEqual(binding.repo_root, repo_path)
            self.assertTrue(binding.markers["runtime_dir"])
            self.assertFalse(binding.markers["valid_meta"])

    def test_repo_with_valid_meta_is_enabled(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex"), exist_ok=True)
            with open(
                os.path.join(repo_path, ".codecortex", "meta.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    {
                        "schema_version": "1.1",
                        "repo_id": "repo-123",
                        "initialized_at": "2026-03-25T00:00:00+00:00",
                    },
                    handle,
                )

            binding = detect_repo_binding(repo_path)

            self.assertTrue(binding.enabled)
            self.assertEqual(binding.repo_root, repo_path)
            self.assertEqual(
                binding.state_dir,
                os.path.join(repo_path, ".codecortex"),
            )
            self.assertTrue(binding.markers["valid_meta"])

    def test_nested_path_binds_to_enabled_repo_root(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex"), exist_ok=True)
            os.makedirs(os.path.join(repo_path, "pkg", "nested"), exist_ok=True)
            with open(
                os.path.join(repo_path, ".codecortex", "meta.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    {
                        "schema_version": "1.1",
                        "repo_id": "repo-123",
                        "initialized_at": "2026-03-25T00:00:00+00:00",
                    },
                    handle,
                )

            binding = detect_repo_binding(os.path.join(repo_path, "pkg", "nested"))

            self.assertEqual(binding.repo_root, repo_path)
            self.assertTrue(binding.enabled)


if __name__ == "__main__":
    unittest.main()
