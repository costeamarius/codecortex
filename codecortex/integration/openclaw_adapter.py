"""OpenClaw runtime transport adapter.

This module defines the executable transport contract between OpenClaw and the
repo-local runtime gateway:

- JSON request in
- JSON response out

The adapter is intentionally thin. OpenClaw remains a runner/integration layer
and forwards structured action envelopes into the canonical runtime gateway.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from codecortex.runtime.gateway import AgentGateway


OPENCLAW_RUNTIME_TRANSPORT = {
    "transport": "json-stdio-v1",
    "request_encoding": "application/json",
    "response_encoding": "application/json",
    "ingress": {
        "command": "cortex action --stdin",
        "request_shape": {
            "action": "string",
            "repo": "string",
            "payload": "object",
            "agent_id": "string|null",
            "environment": "string|null",
        },
    },
    "egress": {
        "response_shape": {
            "status": "string",
            "action": "string",
            "result": "object",
            "policy": "object",
            "memory": "object",
            "error": "object|null",
        }
    },
}


class OpenClawRuntimeAdapter:
    """Translate JSON transport payloads into runtime gateway calls."""

    def __init__(self, gateway: AgentGateway | None = None) -> None:
        self._gateway = gateway or AgentGateway()

    def describe_transport(self) -> Dict[str, Any]:
        return dict(OPENCLAW_RUNTIME_TRANSPORT)

    def handle_json(self, request_json: str | bytes | bytearray) -> str:
        payload = json.loads(request_json)
        response = self._gateway.handle_action(payload)
        return json.dumps(response.to_dict())

    def handle_payload(self, payload: Dict[str, Any]) -> str:
        response = self._gateway.handle_action(payload)
        return json.dumps(response.to_dict())
