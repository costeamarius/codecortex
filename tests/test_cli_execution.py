import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

try:
    from cli.cortex_cli import capabilities, edit_file_command, run_command_cli
    CLI_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment-dependent
    capabilities = None
    edit_file_command = None
    run_command_cli = None
    CLI_IMPORT_ERROR = exc


@unittest.skipIf(CLI_IMPORT_ERROR is not None, f"CLI dependencies unavailable: {CLI_IMPORT_ERROR}")
class CliExecutionTests(unittest.TestCase):
    def test_capabilities_reports_codecortex_enabled_repo(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, "codecortex"), exist_ok=True)
            buffer = StringIO()
            with redirect_stdout(buffer):
                capabilities(path=repo_path)
            payload = json.loads(buffer.getvalue())
            self.assertTrue(payload["codecortex_enabled"])
            self.assertIn("edit-file", payload["execution"]["cli_commands"])

    def test_edit_file_command_prints_machine_readable_result(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
            file_path = os.path.join(repo_path, "sample.py")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("x = 1\n")

            buffer = StringIO()
            with redirect_stdout(buffer):
                edit_file_command(
                    file="sample.py",
                    content="x = 5\n",
                    path=repo_path,
                    agent_id="cli-agent",
                    environment="test",
                    validate=True,
                    lock_ttl_seconds=30,
                )
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["status"], "success")
            with open(file_path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "x = 5\n")

    def test_edit_file_command_failure_result(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
            file_path = os.path.join(repo_path, "config.json")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write('{"timeout": 10}\n')

            buffer = StringIO()
            with redirect_stdout(buffer):
                edit_file_command(
                    file="config.json",
                    content='{"timeout": }\n',
                    path=repo_path,
                    agent_id="cli-agent",
                    environment="test",
                    validate=True,
                    lock_ttl_seconds=30,
                )
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["status"], "failure")
            self.assertEqual(payload["details"]["error_type"], "ValidationError")

    def test_edit_file_command_blocked_result(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
            file_path = os.path.join(repo_path, "sample.py")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("x = 1\n")

            lock_path = os.path.join(repo_path, ".codecortex", "locks", "sample.py.lock.json")
            with open(lock_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "resource": "sample.py",
                        "owner": "other-agent",
                        "created_at": "2026-03-22T00:00:00+00:00",
                        "expires_at": "2999-01-01T00:00:00+00:00",
                    },
                    handle,
                )

            buffer = StringIO()
            with redirect_stdout(buffer):
                edit_file_command(
                    file="sample.py",
                    content="x = 7\n",
                    path=repo_path,
                    agent_id="cli-agent",
                    environment="test",
                    validate=True,
                    lock_ttl_seconds=30,
                )
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["details"]["owner"], "other-agent")

    def test_run_command_cli_prints_machine_readable_result(self):
        with tempfile.TemporaryDirectory() as repo_path:
            buffer = StringIO()
            with redirect_stdout(buffer):
                run_command_cli(
                    command='python3 -c "print(\'cli-ok\')"',
                    path=repo_path,
                    agent_id="cli-agent",
                    environment="test",
                    timeout_seconds=10,
                )
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["status"], "success")
            self.assertIn("cli-ok", payload["details"]["stdout"])

    def test_run_command_cli_failure_result(self):
        with tempfile.TemporaryDirectory() as repo_path:
            buffer = StringIO()
            with redirect_stdout(buffer):
                run_command_cli(
                    command='python3 -c "import sys; sys.exit(4)"',
                    path=repo_path,
                    agent_id="cli-agent",
                    environment="test",
                    timeout_seconds=10,
                )
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["status"], "failure")
            self.assertEqual(payload["details"]["error_type"], "CommandExecutionError")
            self.assertEqual(payload["details"]["returncode"], 4)


if __name__ == "__main__":
    unittest.main()
