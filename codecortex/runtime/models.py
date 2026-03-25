"""Structured models for the runtime boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ActionRequest:
    action: str
    repo: str
    payload: Dict[str, Any] = field(default_factory=dict)
    agent_id: Optional[str] = None
    environment: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ActionRequest":
        return cls(
            action=payload["action"],
            repo=payload["repo"],
            payload=payload.get("payload") or {},
            agent_id=payload.get("agent_id"),
            environment=payload.get("environment"),
        )


@dataclass
class PolicyDecision:
    allowed: bool
    reason: Optional[str] = None
    violations: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Optional[Dict[str, Any]]) -> "PolicyDecision":
        if not payload:
            return cls(allowed=False)
        return cls(
            allowed=payload["allowed"],
            reason=payload.get("reason"),
            violations=list(payload.get("violations") or []),
            details=dict(payload.get("details") or {}),
        )


@dataclass
class MemoryUpdateResult:
    applied: bool
    state_updates: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Optional[Dict[str, Any]]) -> "MemoryUpdateResult":
        if not payload:
            return cls(applied=False)
        return cls(
            applied=payload["applied"],
            state_updates=dict(payload.get("state_updates") or {}),
            details=dict(payload.get("details") or {}),
        )


@dataclass
class RuntimeContext:
    repo: str
    state_dir: Optional[str] = None
    request: Optional[ActionRequest] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)
    graph: Dict[str, Any] = field(default_factory=dict)
    semantics: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    action_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        if self.request is not None:
            payload["request"] = self.request.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "RuntimeContext":
        request_payload = payload.get("request")
        return cls(
            repo=payload["repo"],
            state_dir=payload.get("state_dir"),
            request=ActionRequest.from_dict(request_payload) if request_payload else None,
            meta=dict(payload.get("meta") or {}),
            state=dict(payload.get("state") or {}),
            graph=dict(payload.get("graph") or {}),
            semantics=dict(payload.get("semantics") or {}),
            constraints=dict(payload.get("constraints") or {}),
            decisions=list(payload.get("decisions") or []),
            action_context=dict(payload.get("action_context") or {}),
        )


@dataclass
class ActionResponse:
    status: str
    action: str
    result: Dict[str, Any] = field(default_factory=dict)
    policy: PolicyDecision = field(default_factory=lambda: PolicyDecision(allowed=False))
    memory: MemoryUpdateResult = field(default_factory=lambda: MemoryUpdateResult(applied=False))
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["policy"] = self.policy.to_dict()
        payload["memory"] = self.memory.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ActionResponse":
        return cls(
            status=payload["status"],
            action=payload["action"],
            result=dict(payload.get("result") or {}),
            policy=PolicyDecision.from_dict(payload.get("policy")),
            memory=MemoryUpdateResult.from_dict(payload.get("memory")),
            error=dict(payload["error"]) if payload.get("error") else None,
        )
