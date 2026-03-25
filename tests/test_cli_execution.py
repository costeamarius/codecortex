import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

from codecortex.graph_builder import build_graph, save_graph

try:
    from cli.cortex_cli import action_command, capabilities, edit_file_command, run_command_cli
    CLI_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment-dependent
    action_command = None
    capabilities = None
    edit_file_command = None
    run_command_cli = None
    CLI_IMPORT_ERROR = exc


@unittest.skipIf(CLI_IMPORT_ERROR is not None, f"CLI dependencies unavailable: {CLI_IMPORT_ERROR}")
class CliExecutionTests(unittest.TestCase):
    def _write_runtime_meta(self, repo_path):
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
        with open(
            os.path.join(repo_path, ".codecortex", "state.json"),
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                {
                    "repo_initialized": True,
                    "graph_dirty": False,
                    "last_action_at": None,
                    "last_action_id": None,
                    "last_scan_at": None,
                    "last_scan_commit": None,
                },
                handle,
            )

    def test_action_command_reads_request_file_and_returns_structured_response(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
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
            with open(
                os.path.join(repo_path, ".codecortex", "state.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    {
                        "repo_initialized": True,
                        "graph_dirty": False,
                        "last_action_at": None,
                        "last_action_id": None,
                        "last_scan_at": None,
                        "last_scan_commit": None,
                    },
                    handle,
                )

            file_path = os.path.join(repo_path, "sample.py")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("x = 1\n")

            request_path = os.path.join(repo_path, "request.json")
            with open(request_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "action": "edit_file",
                        "repo": repo_path,
                        "agent_id": "cli-agent",
                        "environment": "test",
                        "payload": {
                            "file": "sample.py",
                            "content": "x = 9\n",
                            "validate": True,
                            "lock_ttl_seconds": 30,
                        },
                    },
                    handle,
                )

            buffer = StringIO()
            with redirect_stdout(buffer):
                action_command(request_file=request_path, stdin=False)

            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["status"], "success")
            self.assertEqual(payload["action"], "edit_file")
            self.assertTrue(payload["policy"]["allowed"])
            self.assertIn("memory", payload)

            with open(file_path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "x = 9\n")

    def test_action_command_reads_request_from_stdin(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
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
            with open(
                os.path.join(repo_path, ".codecortex", "state.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    {
                        "repo_initialized": True,
                        "graph_dirty": False,
                        "last_action_at": None,
                        "last_action_id": None,
                        "last_scan_at": None,
                        "last_scan_commit": None,
                    },
                    handle,
                )

            buffer = StringIO()
            stdin_buffer = StringIO(
                json.dumps(
                    {
                        "action": "run_command",
                        "repo": repo_path,
                        "agent_id": "cli-agent",
                        "environment": "test",
                        "payload": {
                            "command": ["python3", "-c", "print('action-stdin')"],
                            "timeout_seconds": 10,
                        },
                    }
                )
            )
            original_stdin = action_command.__globals__["sys"].stdin
            action_command.__globals__["sys"].stdin = stdin_buffer
            try:
                with redirect_stdout(buffer):
                    action_command(request_file=None, stdin=True)
            finally:
                action_command.__globals__["sys"].stdin = original_stdin

            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["status"], "success")
            self.assertEqual(payload["action"], "run_command")
            self.assertIn("action-stdin", payload["result"]["stdout"])

    def test_capabilities_reports_codecortex_enabled_repo(self):
        with tempfile.TemporaryDirectory() as repo_path:
            state_dir = os.path.join(repo_path, ".codecortex")
            os.makedirs(state_dir, exist_ok=True)
            with open(os.path.join(state_dir, "meta.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.1",
                        "repo_id": "repo-123",
                        "initialized_at": "2026-03-25T00:00:00+00:00",
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "state.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "repo_initialized": True,
                        "graph_dirty": False,
                        "last_action_at": None,
                        "last_action_id": None,
                        "last_scan_at": "2026-03-25T00:00:00+00:00",
                        "last_scan_commit": "abc123",
                    },
                    handle,
                )
            with open(os.path.join(state_dir, "graph.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": "1.0",
                        "git_commit": "abc123",
                        "nodes": [{"id": "file:sample.py", "type": "file", "path": "sample.py"}],
                        "edges": [],
                    },
                    handle,
                )
            buffer = StringIO()
            with redirect_stdout(buffer):
                capabilities(path=repo_path)
            payload = json.loads(buffer.getvalue())
            self.assertTrue(payload["codecortex_enabled"])
            self.assertIn("edit-file", payload["execution"]["cli_commands"])
            self.assertTrue(payload["runtime"]["repo_initialized"])
            self.assertEqual(payload["runtime"]["graph_status"], "fresh")
            self.assertTrue(payload["runtime"]["readiness"]["runtime_actions_available"])

    def test_capabilities_does_not_enable_repo_with_only_advisory_markers(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, "codecortex"), exist_ok=True)
            with open(os.path.join(repo_path, "AGENTS.md"), "w", encoding="utf-8") as handle:
                handle.write("# Agents\n")

            buffer = StringIO()
            with redirect_stdout(buffer):
                capabilities(path=repo_path)
            payload = json.loads(buffer.getvalue())
            self.assertFalse(payload["codecortex_enabled"])
            self.assertTrue(payload["markers"]["codecortex_dir"])
            self.assertTrue(payload["markers"]["agents_md"])
            self.assertFalse(payload["runtime"]["readiness"]["runtime_actions_available"])

    def test_edit_file_command_prints_machine_readable_result(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
            self._write_runtime_meta(repo_path)
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
            self.assertEqual(payload["action"], "edit_file")
            self.assertTrue(payload["policy"]["allowed"])
            self.assertIn("memory", payload)
            self.assertTrue(payload["memory"]["applied"])
            self.assertTrue(payload["memory"]["state_updates"]["graph_dirty"])
            with open(file_path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "x = 5\n")

    def test_edit_file_command_failure_result(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
            self._write_runtime_meta(repo_path)
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
            self.assertEqual(payload["action"], "edit_file")
            self.assertEqual(payload["result"]["error_type"], "ValidationError")
            self.assertTrue(payload["policy"]["allowed"])

    def test_edit_file_command_can_auto_update_graph(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
            os.makedirs(os.path.join(repo_path, "pkg"), exist_ok=True)
            self._write_runtime_meta(repo_path)
            with open(os.path.join(repo_path, "pkg", "__init__.py"), "w", encoding="utf-8") as handle:
                handle.write("")
            module_path = os.path.join(repo_path, "pkg", "module.py")
            with open(module_path, "w", encoding="utf-8") as handle:
                handle.write("def old_name():\n    return 1\n")
            save_graph(build_graph(repo_path, generated_at="t1", git_commit="c1"), repo_path)

            buffer = StringIO()
            with redirect_stdout(buffer):
                edit_file_command(
                    file="pkg/module.py",
                    content="def new_name():\n    return 2\n",
                    path=repo_path,
                    agent_id="cli-agent",
                    environment="test",
                    validate=True,
                    lock_ttl_seconds=30,
                    auto_update_graph=True,
                )

            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["status"], "success")
            self.assertFalse(payload["memory"]["state_updates"]["graph_dirty"])
            self.assertTrue(payload["memory"]["details"]["graph_update"]["applied"])

            with open(os.path.join(repo_path, ".codecortex", "graph.json"), "r", encoding="utf-8") as handle:
                graph = json.load(handle)
            node_ids = {node["id"] for node in graph["nodes"]}
            self.assertIn("function:pkg.module.new_name", node_ids)
            self.assertNotIn("function:pkg.module.old_name", node_ids)

    def test_edit_file_command_blocked_result(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
            self._write_runtime_meta(repo_path)
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
            self.assertEqual(payload["action"], "edit_file")
            self.assertEqual(payload["result"]["owner"], "other-agent")
            self.assertTrue(payload["policy"]["allowed"])

    def test_run_command_cli_prints_machine_readable_result(self):
        with tempfile.TemporaryDirectory() as repo_path:
            self._write_runtime_meta(repo_path)
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
            self.assertEqual(payload["action"], "run_command")
            self.assertIn("cli-ok", payload["result"]["stdout"])
            self.assertTrue(payload["policy"]["allowed"])

    def test_run_command_cli_failure_result(self):
        with tempfile.TemporaryDirectory() as repo_path:
            self._write_runtime_meta(repo_path)
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
            self.assertEqual(payload["action"], "run_command")
            self.assertEqual(payload["result"]["error_type"], "CommandExecutionError")
            self.assertEqual(payload["result"]["returncode"], 4)
            self.assertTrue(payload["policy"]["allowed"])

    def test_run_command_cli_can_auto_update_graph_after_python_mutation(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
            os.makedirs(os.path.join(repo_path, "pkg"), exist_ok=True)
            self._write_runtime_meta(repo_path)
            with open(os.path.join(repo_path, "pkg", "__init__.py"), "w", encoding="utf-8") as handle:
                handle.write("")
            with open(os.path.join(repo_path, "pkg", "module.py"), "w", encoding="utf-8") as handle:
                handle.write("def old_name():\n    return 1\n")
            save_graph(build_graph(repo_path, generated_at="t1", git_commit="c1"), repo_path)

            buffer = StringIO()
            with redirect_stdout(buffer):
                run_command_cli(
                    command=(
                        "python3 -c \"from pathlib import Path; "
                        "Path('pkg/module.py').write_text('def new_name():\\n    return 2\\n', encoding='utf-8')\""
                    ),
                    path=repo_path,
                    agent_id="cli-agent",
                    environment="test",
                    timeout_seconds=10,
                    auto_update_graph=True,
                )

            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["status"], "success")
            self.assertFalse(payload["memory"]["state_updates"]["graph_dirty"])
            self.assertEqual(payload["memory"]["details"]["changed_python_files"], ["pkg/module.py"])
            self.assertTrue(payload["memory"]["details"]["graph_update"]["applied"])

    def test_edit_file_command_blocks_repo_without_valid_meta(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
            file_path = os.path.join(repo_path, "sample.py")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("x = 1\n")

            buffer = StringIO()
            with redirect_stdout(buffer):
                edit_file_command(
                    file="sample.py",
                    content="x = 8\n",
                    path=repo_path,
                    agent_id="cli-agent",
                    environment="test",
                    validate=True,
                    lock_ttl_seconds=30,
                )

            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["status"], "blocked")
            self.assertFalse(payload["policy"]["allowed"])
            self.assertEqual(payload["error"]["error_type"], "RepoNotEnabled")

    def test_edit_file_command_blocks_when_state_json_is_missing(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex", "locks"), exist_ok=True)
            self._write_runtime_meta(repo_path)
            os.remove(os.path.join(repo_path, ".codecortex", "state.json"))
            file_path = os.path.join(repo_path, "sample.py")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("x = 1\n")

            buffer = StringIO()
            with redirect_stdout(buffer):
                edit_file_command(
                    file="sample.py",
                    content="x = 8\n",
                    path=repo_path,
                    agent_id="cli-agent",
                    environment="test",
                    validate=True,
                    lock_ttl_seconds=30,
                )

            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["status"], "blocked")
            self.assertIn("missing or invalid", payload["policy"]["reason"])

    def test_run_command_cli_blocks_denied_effective_program_inside_shell_wrapper(self):
        with tempfile.TemporaryDirectory() as repo_path:
            self._write_runtime_meta(repo_path)
            with open(
                os.path.join(repo_path, ".codecortex", "state.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    {
                        "repo_initialized": True,
                        "graph_dirty": False,
                        "last_action_at": None,
                        "last_action_id": None,
                        "last_scan_at": None,
                        "last_scan_commit": None,
                    },
                    handle,
                )
            with open(
                os.path.join(repo_path, ".codecortex", "constraints.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump({"command_rules": [{"type": "deny_program", "program": "python3"}]}, handle)

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
            self.assertEqual(payload["status"], "blocked")
            self.assertFalse(payload["policy"]["allowed"])
            self.assertIn("python3", payload["policy"]["reason"])


if __name__ == "__main__":
    unittest.main()
