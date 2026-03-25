"""Repo-local memory updates applied after execution."""

from __future__ import annotations

from typing import Any, Dict

from codecortex.execution.logger import append_operation_log, normalize_log_entry
from codecortex.graph_builder import save_graph, update_graph
from codecortex.memory.decision_store import append_decision
from codecortex.memory.state_store import build_initial_runtime_state, build_state_paths
from codecortex.project_context import get_head_commit, read_json, utc_now_iso, write_json
from codecortex.runtime.models import MemoryUpdateResult, RuntimeContext


class MemoryFeedback:
    """Persist minimal repo-local memory updates for executed actions."""

    def apply(self, context: RuntimeContext, result: Dict[str, Any]) -> MemoryUpdateResult:
        request = context.request
        if request is None:
            return MemoryUpdateResult(applied=False, state_updates={})

        paths = build_state_paths(context.repo)
        state_path = paths["state"]
        current_state = read_json(state_path)
        if not isinstance(current_state, dict):
            current_state = dict(context.state) if context.state else build_initial_runtime_state()

        timestamp = utc_now_iso()
        action_id = f"{request.action}:{timestamp}"
        execution_status = result.get("status")
        result_details = result.get("details") or {}
        changed_python_files = self._collect_changed_python_files(
            request.action,
            request.payload,
            execution_status,
            result_details,
        )

        state_updates = {
            "repo_initialized": True,
            "last_action_at": timestamp,
            "last_action_id": action_id,
        }
        if changed_python_files:
            state_updates["graph_dirty"] = True

        graph_update = self._apply_auto_graph_update(
            context=context,
            execution_status=execution_status,
            timestamp=timestamp,
            state_updates=state_updates,
            changed_python_files=changed_python_files,
        )
        decision_update = self._apply_decision_feedback(
            context=context,
            execution_status=execution_status,
            timestamp=timestamp,
        )

        current_state.update(state_updates)
        write_json(state_path, current_state)

        log_payload = normalize_log_entry(
            action=request.action,
            status=execution_status or "failure",
            repo=context.repo,
            target=self._extract_target(request.action, request.payload),
            agent_id=request.agent_id,
            environment=request.environment,
            details={
                "stage": "memory_feedback",
                "state_updates": state_updates,
                "state_path": state_path,
                "execution_status": execution_status,
                "graph_update": graph_update,
                "decision_update": decision_update,
                "changed_python_files": sorted(changed_python_files),
                "result": result_details,
            },
        )
        log_path = append_operation_log(context.repo, log_payload)

        return MemoryUpdateResult(
            applied=True,
            state_updates=state_updates,
            details={
                "stage": "memory_feedback",
                "repo": context.repo,
                "state_path": state_path,
                "log_path": log_path,
                "execution_status": execution_status,
                "graph_update": graph_update,
                "decision_update": decision_update,
                "changed_python_files": sorted(changed_python_files),
            },
        )

    def _collect_changed_python_files(
        self,
        action: str,
        payload: Dict[str, Any],
        execution_status: Any,
        result_details: Dict[str, Any],
    ) -> set[str]:
        if execution_status != "success":
            return set()

        if action == "edit_file":
            target = payload.get("file")
            if isinstance(target, str) and target.endswith(".py"):
                return {target}
            return set()

        if action == "run_command":
            changed_files = result_details.get("changed_python_files")
            if isinstance(changed_files, list):
                return {
                    str(path)
                    for path in changed_files
                    if isinstance(path, str) and path.endswith(".py") and path.strip()
                }

        return set()

    def _apply_auto_graph_update(
        self,
        *,
        context: RuntimeContext,
        execution_status: Any,
        timestamp: str,
        state_updates: Dict[str, Any],
        changed_python_files: set[str],
    ) -> Dict[str, Any]:
        request = context.request
        if request is None:
            return {"attempted": False, "applied": False, "mode": "mark_dirty_only"}

        if not self._should_auto_update_graph(request.payload, execution_status, changed_python_files):
            return {"attempted": False, "applied": False, "mode": "mark_dirty_only"}

        paths = build_state_paths(context.repo)
        existing_graph = read_json(paths["graph"])
        if not isinstance(existing_graph, dict):
            return {
                "attempted": True,
                "applied": False,
                "mode": "auto_update_graph",
                "reason": "graph_missing_or_invalid",
            }

        git_commit = get_head_commit(context.repo)
        updated_graph = update_graph(
            existing_graph=existing_graph,
            repo_path=context.repo,
            changed_files=changed_python_files,
            generated_at=timestamp,
            git_commit=git_commit,
        )
        save_graph(updated_graph, context.repo)

        state_updates["graph_dirty"] = False
        state_updates["last_scan_at"] = timestamp
        state_updates["last_scan_commit"] = git_commit
        return {
            "attempted": True,
            "applied": True,
            "mode": "auto_update_graph",
            "graph_path": paths["graph"],
            "generated_at": timestamp,
            "git_commit": git_commit,
            "changed_files": sorted(changed_python_files),
        }

    def _should_auto_update_graph(
        self,
        payload: Dict[str, Any],
        execution_status: Any,
        changed_python_files: set[str],
    ) -> bool:
        return execution_status == "success" and bool(changed_python_files) and bool(payload.get("auto_update_graph"))

    def _apply_decision_feedback(
        self,
        *,
        context: RuntimeContext,
        execution_status: Any,
        timestamp: str,
    ) -> Dict[str, Any]:
        request = context.request
        if request is None or execution_status != "success":
            return {"requested": False, "applied": False}

        decision_payload = request.payload.get("decision")
        if not isinstance(decision_payload, dict):
            return {"requested": False, "applied": False}

        paths = build_state_paths(context.repo)
        entry = dict(decision_payload)
        entry.setdefault("timestamp", timestamp)
        entry.setdefault("git_commit", get_head_commit(context.repo))
        entry.setdefault("action", request.action)
        if request.agent_id is not None:
            entry.setdefault("agent_id", request.agent_id)
        target = self._extract_target(request.action, request.payload)
        if target is not None:
            references = entry.get("references")
            if not isinstance(references, list):
                references = []
            if target not in references:
                references.append(target)
            entry["references"] = references

        stored_entry = append_decision(paths["decisions"], entry)
        return {
            "requested": True,
            "applied": True,
            "path": paths["decisions"],
            "entry": stored_entry,
        }

    def _extract_target(self, action: str, payload: Dict[str, Any]) -> str | None:
        if action == "edit_file":
            target = payload.get("file")
            return target if isinstance(target, str) else None

        if action == "run_command":
            command = payload.get("command")
            if isinstance(command, (list, tuple)) and command:
                return str(command[0])
            if isinstance(command, str) and command.strip():
                return command

        return None
