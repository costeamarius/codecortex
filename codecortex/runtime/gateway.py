"""Agent-facing ingress for runtime actions."""

from __future__ import annotations

from typing import Any, Dict

from codecortex.runtime.kernel import RuntimeKernel
from codecortex.runtime.models import ActionRequest, ActionResponse


class AgentGateway:
    """Accept structured action payloads and forward them to the runtime kernel."""

    def __init__(self, kernel: RuntimeKernel | None = None):
        self._kernel = kernel or RuntimeKernel()

    def handle_action(self, payload: ActionRequest | Dict[str, Any]) -> ActionResponse:
        if isinstance(payload, ActionRequest):
            request = payload
        else:
            request = ActionRequest.from_dict(payload)
        return self._kernel.handle_action(request)
