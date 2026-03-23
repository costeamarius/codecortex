import json
import os
import tempfile
import time
import unittest

from codecortex.execution.locks import (
    acquire_write_lock,
    build_lock_record,
    compute_expiry,
    get_locks_dir,
    is_lock_expired,
    lock_path_for,
    read_lock,
    release_lock,
    write_lock,
)


class ExecutionLocksTests(unittest.TestCase):
    def test_lock_path_for_uses_local_lock_storage(self):
        with tempfile.TemporaryDirectory() as repo_path:
            path = lock_path_for(repo_path, "pkg/config.json")
            self.assertIn(os.path.join(".codecortex", "locks"), path)
            self.assertTrue(path.endswith("pkg__config.json.lock.json"))

    def test_build_lock_record_contains_owner_and_expiry(self):
        record = build_lock_record("config.json", "agent-1", compute_expiry(30))
        self.assertEqual(record["resource"], "config.json")
        self.assertEqual(record["owner"], "agent-1")
        self.assertIn("created_at", record)
        self.assertIn("expires_at", record)

    def test_write_and_read_lock_roundtrip(self):
        with tempfile.TemporaryDirectory() as repo_path:
            record = build_lock_record("config.json", "agent-1", compute_expiry(30))
            write_lock(repo_path, record)
            loaded = read_lock(repo_path, "config.json")
            self.assertEqual(loaded["owner"], "agent-1")

    def test_release_lock_removes_lock_file(self):
        with tempfile.TemporaryDirectory() as repo_path:
            record = build_lock_record("config.json", "agent-1", compute_expiry(30))
            write_lock(repo_path, record)
            release_lock(repo_path, "config.json")
            self.assertIsNone(read_lock(repo_path, "config.json"))

    def test_acquire_write_lock_blocks_active_lock(self):
        with tempfile.TemporaryDirectory() as repo_path:
            acquired, _ = acquire_write_lock(repo_path, "config.json", "agent-1", ttl_seconds=30)
            self.assertTrue(acquired)
            acquired_second, existing = acquire_write_lock(repo_path, "config.json", "agent-2", ttl_seconds=30)
            self.assertFalse(acquired_second)
            self.assertEqual(existing["owner"], "agent-1")

    def test_expired_lock_can_be_replaced(self):
        with tempfile.TemporaryDirectory() as repo_path:
            expired_record = build_lock_record("config.json", "agent-1", compute_expiry(-1))
            write_lock(repo_path, expired_record)
            self.assertTrue(is_lock_expired(expired_record))

            acquired, new_record = acquire_write_lock(repo_path, "config.json", "agent-2", ttl_seconds=30)
            self.assertTrue(acquired)
            self.assertEqual(new_record["owner"], "agent-2")


if __name__ == "__main__":
    unittest.main()
