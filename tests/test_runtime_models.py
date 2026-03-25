import json
import unittest

from codecortex.runtime.models import (
    ActionRequest,
    ActionResponse,
    MemoryUpdateResult,
    PolicyDecision,
    RuntimeContext,
)


class RuntimeModelsTests(unittest.TestCase):
    def test_action_request_round_trip(self):
        request = ActionRequest(
            action="edit_file",
            repo="/tmp/repo",
            agent_id="agent-1",
            environment="test",
            payload={
                "file": "sample.py",
                "content": "x = 1\n",
                "validate": True,
            },
        )

        encoded = json.dumps(request.to_dict())
        decoded = ActionRequest.from_dict(json.loads(encoded))

        self.assertEqual(decoded, request)

    def test_runtime_context_round_trip(self):
        context = RuntimeContext(
            repo="/tmp/repo",
            state_dir="/tmp/repo/.codecortex",
            request=ActionRequest(
                action="run_command",
                repo="/tmp/repo",
                payload={"command": ["python", "-m", "pytest"]},
            ),
            meta={"schema_version": "1.1"},
            state={"graph_dirty": False},
            graph={"nodes": []},
            semantics={"assertions": []},
            constraints={"constraints": ["stay in repo"]},
            decisions=[{"id": "decision-1"}],
            action_context={"kind": "edit_file", "file": "sample.py"},
        )

        encoded = json.dumps(context.to_dict())
        decoded = RuntimeContext.from_dict(json.loads(encoded))

        self.assertEqual(decoded, context)

    def test_action_response_round_trip(self):
        response = ActionResponse(
            status="success",
            action="edit_file",
            result={"file": "sample.py"},
            policy=PolicyDecision(
                allowed=True,
                reason="allowed by default runtime policy",
                violations=[],
                details={"policy": "placeholder"},
            ),
            memory=MemoryUpdateResult(
                applied=True,
                state_updates={"graph_dirty": True},
                details={"updated": ["state.json"]},
            ),
            error=None,
        )

        encoded = json.dumps(response.to_dict())
        decoded = ActionResponse.from_dict(json.loads(encoded))

        self.assertEqual(decoded, response)


if __name__ == "__main__":
    unittest.main()
