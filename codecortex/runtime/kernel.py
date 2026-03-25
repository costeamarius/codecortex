"""Minimal runtime kernel orchestration."""

from __future__ import annotations

from codecortex.memory.detection import detect_repo_binding
from codecortex.runtime.context_builder import ContextBuilder
from codecortex.runtime.execution_bridge import ExecutionBridge
from codecortex.runtime.memory_feedback import MemoryFeedback
from codecortex.runtime.models import (
    ActionRequest,
    ActionResponse,
    MemoryUpdateResult,
    PolicyDecision,
    RuntimeContext,
)
from codecortex.runtime.policy_engine import PolicyEngine


class RuntimeKernel:
    """Single high-level runtime entry point for supported actions."""

    def __init__(
        self,
        context_builder: ContextBuilder | None = None,
        policy_engine: PolicyEngine | None = None,
        execution_bridge: ExecutionBridge | None = None,
        memory_feedback: MemoryFeedback | None = None,
    ) -> None:
        self._context_builder = context_builder or ContextBuilder()
        self._policy_engine = policy_engine or PolicyEngine()
        self._execution_bridge = execution_bridge or ExecutionBridge()
        self._memory_feedback = memory_feedback or MemoryFeedback()

    def handle_action(self, request: ActionRequest) -> ActionResponse:
        binding = detect_repo_binding(request.repo)
        if not binding.enabled:
            policy = PolicyDecision(
                allowed=False,
                reason="Repository is not CodeCortex-enabled. A valid .codecortex/meta.json is required.",
                details={
                    "repo": binding.repo_root,
                    "meta_path": binding.meta_path,
                    "codecortex_enabled": False,
                },
            )
            return ActionResponse(
                status="blocked",
                action=request.action,
                result={},
                policy=policy,
                memory=MemoryUpdateResult(applied=False),
                error={
                    "error_type": "RepoNotEnabled",
                    "message": policy.reason,
                },
            )

        context = self._build_context(binding.repo_root, request)
        policy = self._evaluate_policy(context)

        if not policy.allowed:
            return ActionResponse(
                status="blocked",
                action=request.action,
                result={},
                policy=policy,
                memory=MemoryUpdateResult(applied=False),
                error={
                    "error_type": "PolicyViolation",
                    "message": policy.reason or "Action blocked by runtime policy.",
                },
            )

        execution_result = self._execute(context)
        memory = self._apply_memory_feedback(context, execution_result.to_dict())
        return ActionResponse(
            status=execution_result.status,
            action=execution_result.action,
            result=execution_result.details,
            policy=policy,
            memory=memory,
            error=None,
        )

    def _build_context(self, repo_root: str, request: ActionRequest) -> RuntimeContext:
        return self._context_builder.build(repo_root, request)

    def _evaluate_policy(self, context: RuntimeContext) -> PolicyDecision:
        return self._policy_engine.evaluate(context)

    def _execute(self, context: RuntimeContext):
        return self._execution_bridge.execute(context)

    def _apply_memory_feedback(self, context: RuntimeContext, result: dict) -> MemoryUpdateResult:
        return self._memory_feedback.apply(context, result)
