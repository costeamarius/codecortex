import os
import json
import tempfile
import unittest
import warnings

from codecortex.integration.openclaw_adapter import OpenClawRuntimeAdapter
from codecortex.openclaw_integration import (
    detect_codecortex_enabled,
    get_openclaw_bootstrap_steps,
    get_openclaw_integration_payload,
    get_openclaw_runtime_bootstrap_plan,
    get_openclaw_runtime_detection,
    get_openclaw_runtime_metadata,
)
from codecortex.runtime.models import ActionResponse, MemoryUpdateResult, PolicyDecision


class SpyGateway:
    def __init__(self):
        self.payload = None

    def handle_action(self, payload):
        self.payload = payload
        return ActionResponse(
            status="success",
            action=payload["action"],
            result={"handled_by": "spy-gateway"},
            policy=PolicyDecision(allowed=True, reason="allowed by runtime policy"),
            memory=MemoryUpdateResult(applied=False),
        )


class OpenClawIntegrationTests(unittest.TestCase):
    def test_openclaw_runtime_adapter_uses_json_transport_contract(self):
        gateway = SpyGateway()
        adapter = OpenClawRuntimeAdapter(gateway=gateway)

        response_json = adapter.handle_json(
            json.dumps(
                {
                    "action": "edit_file",
                    "repo": "/tmp/repo",
                    "agent_id": "openclaw-agent",
                    "environment": "openclaw",
                    "payload": {
                        "file": "sample.py",
                        "content": "value = 1\n",
                    },
                }
            )
        )
        response = json.loads(response_json)

        self.assertIsNotNone(gateway.payload)
        self.assertEqual(gateway.payload["environment"], "openclaw")
        self.assertEqual(gateway.payload["agent_id"], "openclaw-agent")
        self.assertIsInstance(response_json, str)
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["action"], "edit_file")
        self.assertEqual(response["result"]["handled_by"], "spy-gateway")
        self.assertTrue(response["policy"]["allowed"])

    def test_openclaw_runtime_adapter_returns_serialized_json_for_payload_ingress(self):
        gateway = SpyGateway()
        adapter = OpenClawRuntimeAdapter(gateway=gateway)

        response_json = adapter.handle_payload(
            {
                "action": "run_command",
                "repo": "/tmp/repo",
                "agent_id": "openclaw-agent",
                "environment": "openclaw",
                "payload": {"command": ["python3", "-c", "print('ok')"]},
            }
        )
        response = json.loads(response_json)

        self.assertIsInstance(response_json, str)
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["action"], "run_command")
        self.assertEqual(response["result"]["handled_by"], "spy-gateway")

    def test_openclaw_runtime_adapter_describes_json_in_json_out_transport(self):
        payload = OpenClawRuntimeAdapter().describe_transport()

        self.assertEqual(payload["transport"], "json-stdio-v1")
        self.assertEqual(payload["request_encoding"], "application/json")
        self.assertEqual(payload["response_encoding"], "application/json")
        self.assertEqual(payload["ingress"]["command"], "cortex action --stdin")
        self.assertIn("action", payload["ingress"]["request_shape"])
        self.assertIn("status", payload["egress"]["response_shape"])

    def test_detect_codecortex_enabled_requires_valid_meta(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex"), exist_ok=True)
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                payload = detect_codecortex_enabled(repo_path)
            self.assertFalse(payload["codecortex_enabled"])
            self.assertTrue(payload["markers"]["runtime_dir"])
            self.assertFalse(payload["markers"]["valid_meta"])
            self.assertIn("deprecated", str(caught[0].message))

    def test_detect_codecortex_enabled_does_not_use_codecortex_dir_as_authoritative(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, "codecortex"), exist_ok=True)
            payload = get_openclaw_runtime_detection(repo_path)
            self.assertFalse(payload["codecortex_enabled"])
            self.assertTrue(payload["markers"]["codecortex_dir"])

    def test_detect_codecortex_enabled_with_valid_meta(self):
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

            payload = get_openclaw_runtime_detection(repo_path)
            self.assertTrue(payload["codecortex_enabled"])
            self.assertTrue(payload["markers"]["valid_meta"])

    def test_openclaw_integration_payload_exposes_runner_rules(self):
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
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                payload = get_openclaw_integration_payload(repo_path)
            self.assertTrue(payload["openclaw"]["must_use_repo_local_cli"])
            self.assertTrue(payload["openclaw"]["must_not_embed_execution_logic"])
            self.assertTrue(payload["openclaw"]["must_follow_repo_defined_behavior"])
            self.assertTrue(payload["openclaw"]["runtime_ready"])
            self.assertEqual(
                payload["openclaw"]["invocation"]["canonical_runtime_ingress"]["cli_command"],
                "cortex action",
            )
            self.assertEqual(
                payload["openclaw"]["detection"]["readiness_source"],
                "runtime.capabilities",
            )
            self.assertEqual(
                payload["openclaw"]["invocation"]["transport"]["ingress"]["command"],
                "cortex action --stdin",
            )
            self.assertEqual(
                payload["openclaw"]["invocation"]["supported_actions"],
                ["edit_file", "run_command"],
            )
            self.assertIn("deprecated", str(caught[0].message))

    def test_openclaw_integration_payload_reports_runtime_not_ready_for_uninitialized_repo(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, ".codecortex"), exist_ok=True)

            payload = get_openclaw_runtime_metadata(repo_path)

            self.assertFalse(payload["codecortex_enabled"])
            self.assertFalse(payload["openclaw"]["runtime_ready"])
            self.assertIn("not CodeCortex-enabled", " ".join(payload["openclaw"]["warnings"]))
            self.assertEqual(
                payload["openclaw"]["invocation"]["transport"]["transport"],
                "json-stdio-v1",
            )

    def test_openclaw_bootstrap_steps_are_defined(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            payload = get_openclaw_bootstrap_steps()
        self.assertTrue(payload["steps"])
        self.assertIn("bootstrap Codecortex", " ".join(payload["steps"]))
        self.assertIn("cortex action", " ".join(payload["steps"]))
        self.assertIn("deprecated", str(caught[0].message))

    def test_openclaw_runtime_bootstrap_plan_is_defined(self):
        payload = get_openclaw_runtime_bootstrap_plan()
        self.assertTrue(payload["steps"])
        self.assertIn("cortex action", " ".join(payload["steps"]))


if __name__ == "__main__":
    unittest.main()
