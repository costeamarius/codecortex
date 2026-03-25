import unittest

from codecortex.runtime.gateway import AgentGateway
from codecortex.runtime.models import (
    ActionRequest,
    ActionResponse,
    MemoryUpdateResult,
    PolicyDecision,
)


class SpyKernel:
    def __init__(self):
        self.request = None

    def handle_action(self, request: ActionRequest) -> ActionResponse:
        self.request = request
        return ActionResponse(
            status="success",
            action=request.action,
            result={"handled_by": "spy-kernel"},
            policy=PolicyDecision(allowed=True),
            memory=MemoryUpdateResult(applied=False),
        )


class AgentGatewayTests(unittest.TestCase):
    def test_handle_action_forwards_structured_payload_to_kernel(self):
        kernel = SpyKernel()
        gateway = AgentGateway(kernel=kernel)

        response = gateway.handle_action(
            {
                "action": "edit_file",
                "repo": "/tmp/repo",
                "agent_id": "gateway-agent",
                "environment": "test",
                "payload": {
                    "file": "sample.py",
                    "content": "x = 2\n",
                },
            }
        )

        self.assertIsNotNone(kernel.request)
        self.assertEqual(kernel.request.action, "edit_file")
        self.assertEqual(kernel.request.repo, "/tmp/repo")
        self.assertEqual(kernel.request.agent_id, "gateway-agent")
        self.assertEqual(kernel.request.payload["file"], "sample.py")
        self.assertEqual(response.status, "success")
        self.assertEqual(response.result["handled_by"], "spy-kernel")


if __name__ == "__main__":
    unittest.main()
