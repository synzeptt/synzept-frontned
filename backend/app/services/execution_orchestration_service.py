"""Unified execution orchestration service that coordinates the entire execution lifecycle."""

import asyncio
import logging
from uuid import UUID, uuid4
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.execution.engine import ExecutionEngine, ExecutionSession, ExecutionState, ExecutionContext, RunnerRegistry
from app.execution.orchestrator import WorkerOrchestrator
from app.services.execution_persistence_service import ExecutionPersistenceService

logger = logging.getLogger(__name__)


class ExecutionOrchestrationService:
    """
    Unified service that orchestrates the complete execution lifecycle:
    - Execution initialization and persistence
    - Timeline and metrics recording
    - Automatic resume on interruption
    - Event publishing for dashboards
    """

    def __init__(
        self,
        engine: ExecutionEngine,
        persistence_service: ExecutionPersistenceService,
        session: AsyncSession,
    ):
        self.engine = engine
        self.persistence_service = persistence_service
        self.session = session
        self._background_tasks: dict[str, asyncio.Task] = {}

    async def execute_goal(
        self,
        *,
        user_id: UUID | str,
        goal: str,
        workflow_type: str | None = None,
        clarification_answers: dict[str, Any] | None = None,
        approval_decision: str | None = None,
        event_callback: Any | None = None,
        event_stream: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute a user goal through the complete execution lifecycle.
        
        Automatically:
        - Creates execution record
        - Runs planning and workflow inference
        - Initializes timeline and metrics
        - Executes with automatic state persistence
        - Records artifacts and completion
        """
        execution_id = f"exec-{uuid4().hex[:12]}"
        
        try:
            # Initialize execution context
            execution_context = ExecutionContext(
                session=ExecutionSession(
                    id=execution_id,
                    goal=goal,
                    steps=[],
                    state=ExecutionState.PLANNING,
                )
            )
            decision = self._decide_execution(goal, workflow_type)
            execution_context.metadata = {
                "user_id": user_id,
                "workflow_type": workflow_type or "custom",
                "clarification_answers": clarification_answers or {},
                "event_bus": self.engine.event_bus,
                "event_callback": event_callback,
                "event_stream": event_stream or execution_id,
                "decision": decision,
            }
            
            # Build execution plan
            plan = self.engine.orchestrator.build_plan(
                goal=goal,
                context={
                    "execution_id": execution_id,
                    "clarification_answers": clarification_answers or {},
                },
            )
            
            # Create execution session from plan
            session = ExecutionEngine.from_plan(
                goal=goal,
                plan=plan,
            )
            session.metadata["clarification_answers"] = clarification_answers or {}
            session.metadata["worker_plan"] = plan.get("steps", [])
            session.metadata["orchestrator_plan"] = plan
            execution_context.session = session
            
            # Update context with workflow type if inferred
            if plan.get("workflow_type"):
                execution_context.metadata["workflow_type"] = plan["workflow_type"]

            await self._persist_execution_state(
                user_id=user_id,
                execution_id=execution_id,
                session=session,
                execution_context=execution_context,
                status="pending",
                workflow_type=execution_context.metadata["workflow_type"],
                goal=goal,
                approval_pending=decision.get("requires_approval", False),
                approval_data={"reason": decision.get("reason"), "requires_approval": decision.get("requires_approval", False)},
            )

            if decision.get("requires_approval") and approval_decision is None:
                await self._persist_execution_state(
                    user_id=user_id,
                    execution_id=execution_id,
                    session=session,
                    execution_context=execution_context,
                    status="waiting_for_approval",
                    workflow_type=execution_context.metadata["workflow_type"],
                    goal=goal,
                    approval_pending=True,
                    approval_data={"reason": decision.get("reason"), "requires_approval": True},
                )
                await self._emit_event(execution_context, "approval_required", decision.get("reason") or "Approval required before continuing", state=ExecutionState.WAITING_FOR_APPROVAL)
                return {
                    "execution_id": execution_id,
                    "status": "waiting_for_approval",
                    "goal": goal,
                    "decision": decision,
                    "output": None,
                    "error": None,
                    "steps_completed": 0,
                    "total_steps": len(session.steps),
                    "timeline": [],
                    "metrics": {"duration_seconds": 0, "retry_count": 0, "success": False},
                }
            
            if decision["mode"] == "background":
                task = asyncio.create_task(self._execute_background(goal=goal, execution_id=execution_id, session=session, execution_context=execution_context, user_id=user_id, approval_decision=approval_decision, decision=decision))
                self._background_tasks[execution_id] = task
                await self._emit_event(execution_context, "execution_started", "Execution queued for background processing", state=ExecutionState.RUNNING)
                return {
                    "execution_id": execution_id,
                    "status": "queued",
                    "goal": goal,
                    "decision": decision,
                    "output": None,
                    "error": None,
                    "steps_completed": 0,
                    "total_steps": len(session.steps),
                    "timeline": [],
                    "metrics": {"duration_seconds": 0, "retry_count": 0, "success": False},
                }

            result = await self.engine.run(
                session,
                approval_decision=approval_decision,
                context=execution_context,
            )
            return await self._build_result_payload(
                user_id=user_id,
                execution_id=execution_id,
                goal=goal,
                session=session,
                result=result,
                decision=decision,
            )
            
        except Exception as exc:  # noqa: BLE001
            logger.error("Execution failed for goal '%s': %s", goal, exc)
            raise

    async def resume_execution(
        self,
        *,
        user_id: UUID | str,
        execution_id: str,
        approval_decision: str | None = None,
        event_callback: Any | None = None,
        event_stream: str | None = None,
    ) -> dict[str, Any]:
        """Resume a previously interrupted execution."""
        try:
            # Retrieve saved execution state
            saved_state = await self.persistence_service.get_execution_state(
                user_id=user_id,
                execution_id=execution_id,
            )
            
            if not saved_state:
                return {
                    "execution_id": execution_id,
                    "status": "not_found",
                    "error": "Execution not found",
                }
            
            def state_value(key: str, default: Any = None) -> Any:
                if isinstance(saved_state, dict):
                    return saved_state.get(key, default)
                return getattr(saved_state, key, default)

            # Restore and resume
            execution_context = ExecutionContext(session=ExecutionSession(id=execution_id, goal=state_value("goal", ""), steps=[], state=ExecutionState.PENDING))
            execution_context.metadata = {
                "user_id": user_id,
                "workflow_type": state_value("workflow_type", "custom") or "custom",
                "event_callback": event_callback,
                "event_stream": event_stream or execution_id,
                "decision": {"mode": "background" if state_value("status") == "pending" else "immediate", "requires_approval": bool(state_value("approval_pending", False))},
            }
            result = await self.engine.resume(
                user_id=user_id,
                execution_id=execution_id,
                approval_decision=approval_decision,
                context=execution_context,
            )
            
            if not result:
                return {
                    "execution_id": execution_id,
                    "status": "resume_failed",
                    "error": "Failed to resume execution",
                }
            
            return await self._build_result_payload(
                user_id=user_id,
                execution_id=execution_id,
                goal=state_value("goal", ""),
                session=ExecutionSession(id=execution_id, goal=state_value("goal", ""), steps=[], state=ExecutionState.PENDING),
                result=result,
                decision=execution_context.metadata.get("decision", {"mode": "immediate", "requires_approval": False}),
                resumed=True,
            )
            
        except Exception as exc:  # noqa: BLE001
            logger.error("Resume failed for execution %s: %s", execution_id, exc)
            raise

    async def get_execution_status(
        self,
        *,
        user_id: UUID | str,
        execution_id: str,
    ) -> dict[str, Any]:
        """Get current status of an execution including timeline and metrics."""
        saved_state = await self.persistence_service.get_execution_state(
            user_id=user_id,
            execution_id=execution_id,
        )
        
        if not saved_state:
            return {
                "execution_id": execution_id,
                "status": "not_found",
            }
        
        timeline = await self.persistence_service.get_execution_timeline(
            user_id=user_id,
            execution_id=execution_id,
        )
        metrics = await self.persistence_service.get_execution_metrics(
            user_id=user_id,
            execution_id=execution_id,
        )
        
        return {
            "execution_id": execution_id,
            "status": saved_state.status,
            "goal": saved_state.goal,
            "workflow_type": saved_state.workflow_type,
            "current_step": saved_state.current_step_id,
            "current_step_index": saved_state.current_step_index,
            "total_steps": len(saved_state.workflow_steps),
            "approval_pending": saved_state.approval_pending,
            "approval_data": saved_state.approval_data,
            "timeline": [
                {
                    "phase": e.phase,
                    "label": e.label,
                    "status": e.status,
                    "progress": e.progress,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in timeline
            ],
            "metrics": {
                "duration_seconds": metrics.duration_seconds if metrics else 0,
                "retry_count": metrics.retry_count if metrics else 0,
                "success": metrics.success if metrics else False,
                "failure_reason": metrics.failure_reason if metrics else None,
            } if metrics else {},
        }

    def _decide_execution(self, goal: str, workflow_type: str | None = None) -> dict[str, Any]:
        normalized_goal = (goal or "").casefold()
        normalized_workflow = (workflow_type or "").casefold()
        requires_approval = False
        reason = None
        sensitive_keywords = ["purchase", "pay", "payment", "buy", "delete", "submit", "book", "share", "send", "reply"]
        long_running_keywords = ["research", "analyze", "prepare", "draft", "create", "compile", "generate", "report", "document", "presentation", "spreadsheet", "meeting", "review", "compare"]
        if any(keyword in normalized_goal for keyword in sensitive_keywords) or any(keyword in normalized_workflow for keyword in sensitive_keywords):
            requires_approval = True
            reason = "The requested action involves a sensitive or irreversible operation."
        mode = "background" if any(keyword in normalized_goal for keyword in long_running_keywords) else "immediate"
        return {"mode": mode, "requires_approval": requires_approval, "reason": reason}

    async def _persist_execution_state(
        self,
        *,
        user_id: UUID | str,
        execution_id: str,
        session: ExecutionSession,
        execution_context: ExecutionContext,
        status: str,
        workflow_type: str,
        goal: str,
        approval_pending: bool = False,
        approval_data: dict[str, Any] | None = None,
    ) -> None:
        if not self.persistence_service:
            return
        workflow_steps = [
            {
                "id": step.id,
                "title": step.metadata.get("title") or step.action,
                "runner": step.runner,
                "action": step.action,
                "status": step.status,
            }
            for step in session.steps
        ]
        await self.persistence_service.save_execution_state(
            user_id=user_id,
            execution_id=execution_id,
            workflow_type=workflow_type,
            goal=goal,
            status=status,
            current_step_index=session.current_step_index,
            current_step_id=session.steps[0].id if session.steps else None,
            execution_context=execution_context.metadata,
            execution_session={"goal": session.goal, "state": session.state.value},
            workflow_steps=workflow_steps,
            approval_pending=approval_pending,
            approval_data=approval_data or {},
        )

    async def _execute_background(
        self,
        *,
        goal: str,
        execution_id: str,
        session: ExecutionSession,
        execution_context: ExecutionContext,
        user_id: UUID | str,
        approval_decision: str | None = None,
        decision: dict[str, Any],
    ) -> None:
        try:
            await self._emit_event(execution_context, "execution_started", "Execution queued for background processing", state=ExecutionState.RUNNING)
            result = await self.engine.run(session, approval_decision=approval_decision, context=execution_context)
            await self._emit_event(execution_context, "execution_completed", "Execution completed in background mode", state=result.state)
            await self._persist_execution_state(
                user_id=user_id,
                execution_id=execution_id,
                session=session,
                execution_context=execution_context,
                status=result.state.value,
                workflow_type=execution_context.metadata.get("workflow_type") or "custom",
                goal=goal,
                approval_pending=False,
                approval_data=decision,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Background execution failed for %s: %s", execution_id, exc)
            await self._emit_event(execution_context, "execution_failed", str(exc), state=ExecutionState.FAILED)
        finally:
            self._background_tasks.pop(execution_id, None)

    async def _emit_event(self, context: ExecutionContext, event_type: str, message: str, *, state: ExecutionState | None = None) -> None:
        await self.engine._emit_event(context, event_type, message, state=state)

    async def _build_result_payload(
        self,
        *,
        user_id: UUID | str,
        execution_id: str,
        goal: str,
        session: ExecutionSession,
        result: Any,
        decision: dict[str, Any],
        resumed: bool = False,
    ) -> dict[str, Any]:
        if result is None:
            state_name = "failed"
            steps = []
            output = None
            error = "Execution failed"
        else:
            state_name = result.state.value if hasattr(result, "state") else "completed"
            steps = getattr(result, "steps", []) or []
            output = getattr(result, "output", None)
            error = getattr(result, "error", None)

        timeline = []
        metrics = {"duration_seconds": 0, "retry_count": 0, "success": state_name == "completed"}
        if self.persistence_service:
            timeline_items = await self.persistence_service.get_execution_timeline(user_id=user_id, execution_id=execution_id)
            timeline = []
            for item in timeline_items:
                if isinstance(item, dict):
                    timeline.append(
                        {
                            "phase": item.get("phase"),
                            "label": item.get("label"),
                            "status": item.get("status"),
                            "progress": item.get("progress", 0),
                            "timestamp": item.get("timestamp"),
                        }
                    )
                else:
                    timeline.append(
                        {
                            "phase": getattr(item, "phase", None),
                            "label": getattr(item, "label", None),
                            "status": getattr(item, "status", None),
                            "progress": getattr(item, "progress", 0),
                            "timestamp": getattr(item, "timestamp", None).isoformat() if getattr(item, "timestamp", None) is not None else None,
                        }
                    )
            metrics_item = await self.persistence_service.get_execution_metrics(user_id=user_id, execution_id=execution_id)
            if metrics_item:
                if isinstance(metrics_item, dict):
                    metrics = {
                        "duration_seconds": metrics_item.get("duration_seconds") or 0,
                        "retry_count": metrics_item.get("retry_count") or 0,
                        "success": bool(metrics_item.get("success", False)),
                        "failure_reason": metrics_item.get("failure_reason"),
                    }
                else:
                    metrics = {
                        "duration_seconds": getattr(metrics_item, "duration_seconds", 0) or 0,
                        "retry_count": getattr(metrics_item, "retry_count", 0) or 0,
                        "success": bool(getattr(metrics_item, "success", False)),
                        "failure_reason": getattr(metrics_item, "failure_reason", None),
                    }

        status = state_name
        if decision.get("requires_approval") and state_name in {"waiting_for_approval", "pending"}:
            status = "waiting_for_approval"
        if resumed and state_name == "completed":
            status = "completed"

        return {
            "execution_id": execution_id,
            "status": status,
            "goal": goal,
            "decision": decision,
            "output": output,
            "error": error,
            "steps_completed": len([step for step in steps if getattr(step, "status", None) == "completed"]),
            "total_steps": len(steps),
            "timeline": timeline,
            "metrics": metrics,
            "resumed": resumed,
        }
