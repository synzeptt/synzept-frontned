from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from types import SimpleNamespace
from typing import Any, Protocol
from uuid import UUID

from app.agents.planner import Planner
from app.execution.approval import ApprovalEngine
from app.execution.artifacts import Artifact
from app.execution.clarification import ClarificationEngine
from app.execution.context import SharedExecutionContext
from app.execution.learning import ExecutionLearningStore
from app.execution.orchestrator import WorkerOrchestrator
from app.execution.state_machine import ExecutionLifecycleState, ExecutionStateMachine
from app.services.execution_persistence_service import ExecutionPersistenceService
from app.skills.dispatcher import SkillDispatcher
from app.skills.result import SkillExecutionStatus

logger = logging.getLogger(__name__)


class ExecutionEventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[callable]] = {}
        self._history: dict[str, list[dict[str, Any]]] = {}

    def subscribe(self, execution_id: str, callback: callable) -> None:
        self._subscribers.setdefault(execution_id, []).append(callback)

    def publish(self, execution_id: str, event: dict[str, Any]) -> None:
        self._history.setdefault(execution_id, []).append(event)
        for callback in self._subscribers.get(execution_id, []):
            callback(event)

    def history(self, execution_id: str) -> list[dict[str, Any]]:
        return list(self._history.get(execution_id, []))


class ExecutionRegistry:
    def __init__(self) -> None:
        self._runners: dict[str, str] = {}

    def register(self, runner_name: str, implementation: str) -> None:
        self._runners[runner_name.casefold()] = implementation

    def resolve(self, runner_name: str) -> str | None:
        return self._runners.get(runner_name.casefold())


class ExecutionState(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    WAITING_FOR_INFORMATION = "waiting_for_information"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class ExecutionStep:
    id: str
    runner: str
    action: str
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    output: Any | None = None
    error: str | None = None


@dataclass(slots=True)
class ExecutionSession:
    id: str
    goal: str
    steps: list[ExecutionStep]
    state: ExecutionState = ExecutionState.PENDING
    current_step_index: int = 0
    approval_decision: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExecutionContext:
    session: ExecutionSession
    logger: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExecutionResult:
    state: ExecutionState
    steps: list[ExecutionStep]
    output: Any | None = None
    error: str | None = None
    result: Any | None = None


class StepExecutor(Protocol):
    name: str

    async def execute(self, *, step: ExecutionStep, context: ExecutionContext) -> dict[str, Any]:
        ...


class RunnerRegistry:
    def __init__(self) -> None:
        self._runners: dict[str, StepExecutor] = {}

    def register(self, runner_id: str, executor: StepExecutor) -> None:
        self._runners[runner_id] = executor

    def get(self, runner_id: str) -> StepExecutor | None:
        return self._runners.get(runner_id)


class ExecutionEngine:
    def __init__(self, runners: RunnerRegistry, persistence_service: ExecutionPersistenceService | None = None) -> None:
        self.runners = runners
        self.clarification_engine = ClarificationEngine()
        self.approval_engine = ApprovalEngine()
        self.orchestrator = WorkerOrchestrator()
        self.state_machine = ExecutionStateMachine()
        self.persistence_service = persistence_service
        self.event_bus = ExecutionEventBus()
        self.execution_learning_store = None
        self.skill_dispatcher = SkillDispatcher()
        self._planner = Planner()

    @classmethod
    def from_plan(cls, *, goal: str, plan: dict[str, Any], step_prefix: str = "step") -> ExecutionSession:
        steps_payload = plan.get("steps") or []
        if not steps_payload:
            steps_payload = [{"id": "execute", "title": goal, "runner": "generic", "action": "execute"}]
        steps = []
        for index, step in enumerate(steps_payload, start=1):
            runner_id = str(step.get("runner") or step.get("worker_id") or "generic")
            plan_metadata = step.get("metadata") if isinstance(step.get("metadata"), dict) else {}
            metadata = {
                "plan_step": step,
                "goal": goal,
                "title": step.get("title") or step.get("action") or f"{step_prefix}-{index}",
                "expected_output": step.get("expected_output") or "",
                "requires_approval": bool(step.get("worker_requires_approval") or step.get("requires_approval")),
                "depends_on": step.get("depends_on") or step.get("dependencies") or [],
                "worker_id": step.get("worker_id") or step.get("runner"),
            }
            metadata.update(plan_metadata)
            steps.append(
                ExecutionStep(
                    id=str(step.get("id") or f"{step_prefix}-{index}"),
                    runner=runner_id,
                    action=str(step.get("action") or step.get("title") or f"{step_prefix}-{index}"),
                    metadata=metadata,
                )
            )
        return ExecutionSession(id=f"plan-{goal[:12].strip()}", goal=goal, steps=steps)

    async def resume(
        self,
        *,
        user_id: UUID | str,
        execution_id: str,
        approval_decision: str | None = None,
        context: ExecutionContext | None = None,
    ) -> ExecutionResult | None:
        """
        Resume a previously saved execution.
        
        Returns the execution result if execution was resumed, or None if execution not found.
        """
        if not self.persistence_service:
            logger.warning("Persistence service not configured; cannot resume execution")
            return None
        
        try:
            # Retrieve saved execution state
            saved_state = await self.persistence_service.get_execution_state(
                user_id=user_id,
                execution_id=execution_id,
            )
            
            if not saved_state:
                logger.debug("No saved execution state found for %s", execution_id)
                return None
            
            # Restore execution session from saved state
            session = await self._restore_session_from_state(saved_state)
            
            # Create execution context if not provided
            execution_context = context or ExecutionContext(session=session)
            execution_context.metadata["user_id"] = user_id
            if isinstance(saved_state, dict):
                execution_context.metadata["workflow_type"] = saved_state.get("workflow_type") or "custom"
            else:
                execution_context.metadata["workflow_type"] = getattr(saved_state, "workflow_type", None) or "custom"
            execution_context.metadata["_execution_start_time"] = datetime.utcnow()
            execution_context.metadata["_persistence_initialized"] = True
            execution_context.metadata["_resumed"] = True
            
            current_step_index = saved_state.current_step_index if not isinstance(saved_state, dict) else saved_state.get("current_step_index", 0)
            logger.info("Resuming execution %s from step %d/%d", execution_id, current_step_index, len(session.steps))
            
            # Resume from the saved point
            return await self.run(session, approval_decision=approval_decision, context=execution_context)
            
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to resume execution %s: %s", execution_id, exc)
            return None

    async def _restore_session_from_state(self, saved_state: Any) -> ExecutionSession:
        """Restore an ExecutionSession from a saved execution state payload."""
        def state_value(key: str, default: Any = None) -> Any:
            if isinstance(saved_state, dict):
                return saved_state.get(key, default)
            return getattr(saved_state, key, default)

        # Convert saved workflow steps to ExecutionStep objects
        steps = []
        for step_data in state_value("workflow_steps") or []:
            if isinstance(step_data, dict):
                step_id = step_data.get("id", f"step-{len(steps)}")
                runner = step_data.get("runner", "generic")
                action = step_data.get("title", step_data.get("action", f"step-{len(steps)}"))
                metadata = {"title": step_data.get("title", ""), "status": step_data.get("status", "pending")}
                status = step_data.get("status", "pending")
            else:
                step_id = getattr(step_data, "id", f"step-{len(steps)}")
                runner = getattr(step_data, "runner", "generic")
                action = getattr(step_data, "title", getattr(step_data, "action", f"step-{len(steps)}"))
                metadata = {"title": getattr(step_data, "title", ""), "status": getattr(step_data, "status", "pending")}
                status = getattr(step_data, "status", "pending")
            steps.append(
                ExecutionStep(
                    id=step_id,
                    runner=runner,
                    action=action,
                    metadata=metadata,
                    status=status,
                )
            )
        
        # Map saved status to ExecutionState enum
        status_map = {
            "pending": ExecutionState.PENDING,
            "planning": ExecutionState.PLANNING,
            "running": ExecutionState.RUNNING,
            "waiting_for_information": ExecutionState.WAITING_FOR_INFORMATION,
            "waiting_for_approval": ExecutionState.WAITING_FOR_APPROVAL,
            "completed": ExecutionState.COMPLETED,
            "failed": ExecutionState.FAILED,
        }
        
        session = ExecutionSession(
            id=state_value("execution_id", "resume-session"),
            goal=state_value("goal", ""),
            steps=steps,
            state=status_map.get(state_value("status", "pending"), ExecutionState.PENDING),
            current_step_index=state_value("current_step_index") or 0,
            metadata={
                "clarification_answers": state_value("clarification_answers") or {},
                "progress": state_value("progress_log") or [],
                "error_log": state_value("error_log") or [],
            },
        )
        
        return session

    async def run(self, session: ExecutionSession, *, approval_decision: str | None = None, context: ExecutionContext | None = None) -> ExecutionResult:
        execution_context = context or ExecutionContext(session=session)
        self.execution_learning_store = execution_context.metadata.get("execution_learning_store") if isinstance(execution_context.metadata.get("execution_learning_store"), ExecutionLearningStore) else None
        start_time = time.time()
        if self.execution_learning_store is None and execution_context.metadata.get("execution_learning_store") is not None:
            self.execution_learning_store = execution_context.metadata.get("execution_learning_store")
        
        # Extract user_id and execution_id from context metadata
        user_id = execution_context.metadata.get("user_id") if isinstance(execution_context.metadata, dict) else None
        workflow_type = execution_context.metadata.get("workflow_type") if isinstance(execution_context.metadata, dict) else None
        
        # Initialize persistence and timeline if service is available
        if self.persistence_service and user_id:
            await self._initialize_execution_persistence(
                user_id=user_id,
                execution_id=session.id,
                workflow_type=workflow_type or "custom",
                goal=session.goal,
                execution_context=execution_context,
            )
        
        if session.state == ExecutionState.COMPLETED:
            return ExecutionResult(state=session.state, steps=session.steps, output=session.metadata.get("last_output"))
        shared_context = self._shared_context(session, execution_context)
        self._transition_state(session, shared_context, ExecutionLifecycleState.PLANNING)
        clarification = self.clarification_engine.analyze(goal=session.goal, existing_answers=session.metadata.get("clarification_answers", {}))
        session.metadata["clarification_state"] = clarification
        shared_context.clarification_answers = session.metadata.get("clarification_answers", {})
        if clarification.get("needs_clarification") and not (approval_decision == "approve" and execution_context.metadata.get("_resumed")):
            session.state = ExecutionState.WAITING_FOR_INFORMATION
            self._transition_state(session, shared_context, ExecutionLifecycleState.CLARIFYING)
            await self._emit_event(execution_context, "clarification_requested", clarification.get("next_question") or "Clarification required", state=session.state)
            # Persist clarification state
            user_id = execution_context.metadata.get("user_id") if isinstance(execution_context.metadata, dict) else None
            if self.persistence_service and user_id:
                await self._update_execution_persistence(
                    user_id=user_id,
                    execution_id=session.id,
                    session=session,
                    execution_context=execution_context,
                    phase="clarification",
                )
            return ExecutionResult(state=session.state, steps=session.steps, output=clarification.get("next_question"), result={"clarification": clarification})
        await self._emit_event(execution_context, "execution_started", "Execution started", state=ExecutionState.RUNNING)
        if approval_decision == "approve" and session.state == ExecutionState.WAITING_FOR_APPROVAL:
            session.approval_decision = approval_decision
            session.state = ExecutionState.RUNNING
            if session.steps:
                for step in session.steps:
                    if step.status == "waiting" and (step.metadata.get("approval_required") or step.metadata.get("worker_state") == "waiting"):
                        if step.metadata.get("approval_source") == "runner":
                            step.status = "completed"
                            step.metadata["worker_state"] = "completed"
                            step.output = step.output or "approved"
                        else:
                            step.status = "pending"
                            step.metadata["worker_state"] = "pending"
                            step.output = None
                        break
                shared_context.approval_status = "approved"
        elif approval_decision == "reject" and session.state == ExecutionState.WAITING_FOR_APPROVAL:
            session.approval_decision = approval_decision
            session.state = ExecutionState.FAILED
            session.steps[-1].status = "failed"
            session.steps[-1].error = "approval rejected"
            # Persist failure and finalize
            user_id = execution_context.metadata.get("user_id") if isinstance(execution_context.metadata, dict) else None
            result = ExecutionResult(state=session.state, steps=session.steps, error="approval rejected")
            if self.persistence_service and user_id:
                await self._finalize_execution_persistence(
                    user_id=user_id,
                    execution_id=session.id,
                    session=session,
                    execution_context=execution_context,
                    result=result,
                )
            return result

        if session.state in {ExecutionState.PENDING, ExecutionState.PLANNING}:
            session.state = ExecutionState.RUNNING
            self._transition_state(session, shared_context, ExecutionLifecycleState.EXECUTING)

        last_result: Any | None = None
        step_lookup = {step.id: step for step in session.steps}
        runtime_metrics = {
            "total_workers": len(session.steps),
            "workers_completed": 0,
            "workers_failed": 0,
            "parallel_execution_count": 0,
            "dependency_wait_time": 0,
            "recovery_attempts": 0,
            "verification_success": 0,
            "artifact_propagation_count": 0,
            "context_sync_events": 0,
        }
        shared_context.metadata["runtime_metrics"] = runtime_metrics

        if plan_payload := self._extract_skill_dispatch_payload(session, execution_context):
            session.metadata["planner_output"] = plan_payload
            session.metadata["progress"] = session.metadata.get("progress", []) + ["Understanding request", "Planning execution", f"Selecting {plan_payload.get('selected_skill', 'skill')} Skill"]
            await self._emit_event(execution_context, "skill_dispatch_started", f"Dispatching {plan_payload.get('selected_skill', 'skill')} skill", state=session.state)
            result = self.skill_dispatcher.dispatch(plan_payload)
            session.metadata["progress"] = session.metadata.get("progress", []) + ["Creating Event" if plan_payload.get("selected_skill") == "calendar" else "Executing Skill", "Verifying Event", "Completed"]
            if result.status == SkillExecutionStatus.SUCCESS:
                step_output = result.outputs.get("result") or result.outputs
                session.metadata["last_output"] = step_output
                session.metadata.setdefault("artifacts", []).extend(result.outputs.get("artifacts", []))
                session.steps = [ExecutionStep(id="skill-dispatch", runner=plan_payload.get("selected_skill") or "skill", action=plan_payload.get("action") or "dispatch", metadata={"skill": plan_payload.get("selected_skill"), "artifacts": result.outputs.get("artifacts", []), "verification": result.outputs.get("verification")}, status="completed", output=step_output)]
                session.state = ExecutionState.COMPLETED
                self._transition_state(session, shared_context, ExecutionLifecycleState.COMPLETED)
                shared_context.artifacts = result.outputs.get("artifacts", [])
                shared_context.metadata["verification_results"] = [result.outputs.get("verification")] if isinstance(result.outputs.get("verification"), dict) else []
                await self._emit_event(execution_context, "execution_completed", "Execution completed", state=session.state)
                return ExecutionResult(state=session.state, steps=session.steps, output=step_output, result={"completed": True, "artifacts": result.outputs.get("artifacts", []), "verification": result.outputs.get("verification")})
            session.state = ExecutionState.FAILED
            self._transition_state(session, shared_context, ExecutionLifecycleState.FAILED)
            await self._emit_event(execution_context, "execution_failed", "Execution failed", state=session.state)
            return ExecutionResult(state=session.state, steps=session.steps, output=result.message, result={"failed": True, "error": result.message})

        while True:
            pending_steps = [step for step in session.steps if step.status not in {"completed", "skipped", "failed", "cancelled"}]
            if not pending_steps:
                break

            ready_steps = []
            for step in pending_steps:
                if step.status == "running":
                    continue
                if self._step_ready(step, step_lookup, shared_context):
                    ready_steps.append(step)
                elif step.status not in {"waiting"}:
                    step.status = "waiting"
                    step.metadata["worker_state"] = "waiting"

            if not ready_steps:
                break

            batch = sorted(ready_steps, key=lambda item: item.id)
            runtime_metrics["parallel_execution_count"] = max(runtime_metrics["parallel_execution_count"], len(batch))
            for step in batch:
                step.status = "running"
                step.metadata["worker_state"] = "running"
                session.current_step_index = max(session.current_step_index, session.steps.index(step) + 1)
                shared_context.current_worker = step.runner
                shared_context.current_step = step.action
                self._transition_state(session, shared_context, ExecutionLifecycleState.EXECUTING)
                await self._emit_event(execution_context, "step_started", f"Running step {step.id}", step=step, state=session.state)

            results = []
            for index, step in enumerate(batch):
                result = await self._execute_step(step, execution_context, shared_context, session)
                results.append(result)
                if step.status == "waiting":
                    for deferred_step in batch[index + 1:]:
                        deferred_step.status = "pending"
                        deferred_step.metadata["worker_state"] = "pending"
                    session.state = ExecutionState.WAITING_FOR_APPROVAL
                    self._transition_state(session, shared_context, ExecutionLifecycleState.WAITING_FOR_APPROVAL)
                    await self._emit_event(execution_context, "approval_required", "Approval required before continuing", step=step, state=session.state)
                    user_id = execution_context.metadata.get("user_id") if isinstance(execution_context.metadata, dict) else None
                    if self.persistence_service and user_id:
                        await self._update_execution_persistence(
                            user_id=user_id,
                            execution_id=session.id,
                            session=session,
                            execution_context=execution_context,
                            phase="approval",
                        )
                    return ExecutionResult(state=session.state, steps=session.steps, output=step.output, result=result.get("result"))
                if result.get("status") == "failed" or step.status == "failed":
                    runtime_metrics["workers_failed"] += 1
                    session.metadata.setdefault("error_log", []).append({"step_id": step.id, "error": step.error})
                    last_result = result.get("result")
                    recovery = await self._recover_step(step, execution_context, shared_context, session, result)
                    if recovery.get("recovered"):
                        runtime_metrics["recovery_attempts"] += 1
                        session.metadata.setdefault("recovery_metrics", {"recovery_count": 0, "recovery_types": [], "recovery_success": 0, "time_lost_seconds": 0})
                        session.metadata["recovery_metrics"]["recovery_count"] += 1
                        session.metadata["recovery_metrics"]["recovery_types"].append(recovery["type"])
                        session.metadata["recovery_metrics"]["recovery_success"] += 1
                        await self._emit_event(execution_context, "step_recovered", f"Step {step.id} recovered with {recovery['type']}", step=step, state=session.state)
                        continue
                    await self._emit_event(execution_context, "step_failed", f"Step {step.id} failed", step=step, state=session.state)
                    continue
                if result.get("status") == "completed" or step.status == "completed":
                    runtime_metrics["workers_completed"] += 1
                    session.metadata["last_output"] = step.output
                    last_result = result.get("result")
                    shared_context.metadata["completed_steps"] = shared_context.metadata.get("completed_steps", []) + [step.id]
                    shared_context.metadata["context_sync_events"] = shared_context.metadata.get("context_sync_events", 0) + 1
                    runtime_metrics["context_sync_events"] = shared_context.metadata["context_sync_events"]
                    await self._emit_event(execution_context, "step_completed", f"Step {step.id} completed", step=step, state=session.state)
                    user_id = execution_context.metadata.get("user_id") if isinstance(execution_context.metadata, dict) else None
                    if self.persistence_service and user_id:
                        await self._update_execution_persistence(
                            user_id=user_id,
                            execution_context=execution_context,
                            execution_id=session.id,
                            session=session,
                            phase="execution",
                        )

        self._transition_state(session, shared_context, ExecutionLifecycleState.GENERATING_ARTIFACTS)
        if any(step.status == "failed" for step in session.steps):
            session.state = ExecutionState.FAILED
            self._transition_state(session, shared_context, ExecutionLifecycleState.FAILED)
        else:
            session.state = ExecutionState.COMPLETED
            self._transition_state(session, shared_context, ExecutionLifecycleState.COMPLETED)

        runtime_metrics["execution_duration"] = round(time.time() - start_time, 3)
        if self.execution_learning_store is not None:
            await self._record_execution_learning(session, execution_context, shared_context, runtime_metrics)

        await self._emit_event(execution_context, "execution_completed", "Execution completed", state=session.state)

        verification_results = shared_context.metadata.get("verification_results", [])
        verification_passed = all(check.get("status") in {"passed", "skipped"} for check in verification_results) if verification_results else False
        artifact_titles = [artifact.get("title") for artifact in shared_context.artifacts if isinstance(artifact, dict) and artifact.get("title")]
        result = ExecutionResult(
            state=session.state,
            steps=session.steps,
            output=session.metadata.get("last_output"),
            result={
                "completed_workers": [step.id for step in session.steps if step.status == "completed"],
                "failed_workers": [step.id for step in session.steps if step.status == "failed"],
                "artifacts": [artifact for artifact in shared_context.artifacts],
                "artifact_titles": artifact_titles,
                "verification_results": verification_results,
                "verification_status": "passed" if verification_passed else "failed",
                "execution_duration": runtime_metrics["execution_duration"],
                "recovery_attempts": runtime_metrics["recovery_attempts"],
                "timeline_summary": session.metadata.get("progress", []),
                "runtime_metrics": runtime_metrics,
                "capabilities_used": self._infer_capabilities(session),
                "learning_recorded": self.execution_learning_store is not None,
                "completion_summary": self._build_completion_summary(session, shared_context, runtime_metrics, verification_passed),
                "shared_context": {
                    "artifact_count": len(shared_context.artifacts),
                    "current_worker": shared_context.current_worker,
                    "current_step": shared_context.current_step,
                },
            },
        )
        if last_result is not None:
            result.result["last_result"] = last_result
        user_id = execution_context.metadata.get("user_id") if isinstance(execution_context.metadata, dict) else None
        if self.persistence_service and user_id:
            await self._finalize_execution_persistence(
                user_id=user_id,
                execution_id=session.id,
                session=session,
                execution_context=execution_context,
                result=result,
            )

        return result

    async def _record_execution_learning(self, session: ExecutionSession, execution_context: ExecutionContext, shared_context: SharedExecutionContext, runtime_metrics: dict[str, Any]) -> None:
        if self.execution_learning_store is None:
            return
        attempt_count = max(sum(int(step.metadata.get("attempt_count", 0) or 0) for step in session.steps), 0)
        capabilities_used = self._infer_capabilities(session)
        knowledge = {
            "goal": session.goal,
            "task_type": self._infer_task_type(session.goal),
            "capabilities_used": capabilities_used,
            "workers_used": list({step.runner for step in session.steps if step.runner}),
            "execution_graph": [step.action for step in session.steps],
            "recovery_events": shared_context.metadata.get("recovery_events", []),
            "verification_results": shared_context.metadata.get("verification_results", []),
            "execution_duration": runtime_metrics.get("context_sync_events", 0),
            "retry_count": max(sum(int(step.metadata.get("attempt_count", 0) or 0) for step in session.steps), 0),
            "failures": [step.error for step in session.steps if getattr(step, "error", None)],
            "successful_recovery_strategy": self._successful_recovery_strategy(session),
            "artifacts_produced": [artifact.get("name") for artifact in shared_context.artifacts if isinstance(artifact, dict) and artifact.get("name")],
            "overall_outcome": "success" if session.state == ExecutionState.COMPLETED else "failed",
            "capability_stats": self._build_capability_stats(session, runtime_metrics),
            "execution_duration": max(1, int(runtime_metrics.get("parallel_execution_count", 0) or 0)),
            "retry_count": max(0, attempt_count - len(session.steps)),
        }
        if session.state == ExecutionState.FAILED:
            knowledge["failure_reason"] = "; ".join(step.error for step in session.steps if getattr(step, "error", None))
            knowledge["missing_permissions"] = [error for error in knowledge["failures"] if "permission" in str(error).lower()]
            knowledge["missing_information"] = []
        user_id = execution_context.metadata.get("user_id") if isinstance(execution_context.metadata, dict) else None
        await self.execution_learning_store.record(user_id=user_id, knowledge=knowledge)

    def _infer_capabilities(self, session: ExecutionSession) -> list[str]:
        goal = session.goal.casefold()
        capabilities = []
        if any(keyword in goal for keyword in ["research", "compare", "investigate", "find", "latest"]):
            capabilities.append("research")
        if any(keyword in goal for keyword in ["email", "message", "send"]):
            capabilities.append("email")
        if any(keyword in goal for keyword in ["meeting", "calendar", "schedule"]):
            capabilities.append("calendar")
        if any(keyword in goal for keyword in ["browser", "website", "web page", "browse"]):
            capabilities.append("browser")
        if any(keyword in goal for keyword in ["document", "file", "folder", "organize"]):
            capabilities.append("file")
        if any(keyword in goal for keyword in ["write", "report", "draft", "presentation"]):
            capabilities.append("writing")
        return capabilities or ["planning"]

    def _infer_task_type(self, goal: str) -> str:
        lowered = goal.casefold()
        if any(keyword in lowered for keyword in ["research", "find", "investigate", "compare"]):
            return "research"
        if any(keyword in lowered for keyword in ["email", "message", "send"]):
            return "communication"
        if any(keyword in lowered for keyword in ["meeting", "calendar", "schedule"]):
            return "scheduling"
        return "execution"

    def _successful_recovery_strategy(self, session: ExecutionSession) -> str | None:
        for step in session.steps:
            strategy = step.metadata.get("recovery_strategy")
            if strategy:
                return strategy
        return None

    def _build_capability_stats(self, session: ExecutionSession, runtime_metrics: dict[str, Any]) -> dict[str, Any]:
        stats: dict[str, Any] = {}
        shared_context = session.metadata.get("shared_context")
        verification_success = 1 if shared_context else 0
        capabilities = self._infer_capabilities(session)
        if not capabilities:
            capabilities = [step.runner for step in session.steps if step.runner]
        for capability in capabilities:
            stats[capability] = {
                "success_count": 1 if session.state == ExecutionState.COMPLETED else 0,
                "failure_count": 1 if session.state == ExecutionState.FAILED else 0,
                "recovery_success": 1 if self._successful_recovery_strategy(session) else 0,
                "verification_success": verification_success,
                "average_duration": runtime_metrics.get("parallel_execution_count", 0),
            }
        for step in session.steps:
            if step.runner and step.runner not in stats:
                inferred_capability = step.runner.split("-")[0]
                stats[inferred_capability] = {
                    "success_count": 1 if session.state == ExecutionState.COMPLETED else 0,
                    "failure_count": 1 if session.state == ExecutionState.FAILED else 0,
                    "recovery_success": 1 if self._successful_recovery_strategy(session) else 0,
                    "verification_success": verification_success,
                    "average_duration": runtime_metrics.get("parallel_execution_count", 0),
                }
        return stats

    def _build_completion_summary(self, session: ExecutionSession, shared_context: SharedExecutionContext, runtime_metrics: dict[str, Any], verification_passed: bool) -> str:
        completed = len([step for step in session.steps if step.status == "completed"])
        failed = len([step for step in session.steps if step.status == "failed"])
        artifacts = len(shared_context.artifacts)
        recoveries = runtime_metrics.get("recovery_attempts", 0)
        capability_list = ", ".join(self._infer_capabilities(session))
        summary = [
            f"Goal: {session.goal}",
            f"State: {session.state.value}",
            f"Capabilities used: {capability_list}",
            f"Completed steps: {completed}",
            f"Failed steps: {failed}",
            f"Artifacts created: {artifacts}",
            f"Verification: {'passed' if verification_passed else 'failed'}",
            f"Recovery attempts: {recoveries}",
            f"Duration: {runtime_metrics.get('execution_duration', 0)}s",
        ]
        if recoveries > 0:
            summary.append("Recovery strategy was applied to preserve execution quality.")
        if artifacts:
            summary.append("High-quality artifacts were produced and saved.")
        return " \n".join(summary)

    def _step_ready(self, step: ExecutionStep, step_lookup: dict[str, ExecutionStep], shared_context: SharedExecutionContext) -> bool:
        dependencies = step.metadata.get("depends_on") or []
        if not dependencies and not step.metadata.get("requires"):
            return True
        for dependency in list(dependencies) + list(step.metadata.get("requires") or []):
            if dependency in step_lookup:
                if step_lookup[dependency].status != "completed":
                    return False
            elif shared_context.metadata.get(dependency) is None and not any(getattr(artifact, "get", lambda *_: None)("name") == dependency for artifact in shared_context.artifacts):
                return False
        return True

    def _extract_skill_dispatch_payload(self, session: ExecutionSession, execution_context: ExecutionContext) -> dict[str, Any] | None:
        planner_output = session.metadata.get("planner_output") or {}
        if planner_output.get("selected_skill") or planner_output.get("skill") or planner_output.get("capability"):
            return planner_output
        plan_payload = execution_context.metadata.get("planner_output") if isinstance(execution_context.metadata, dict) else None
        if isinstance(plan_payload, dict) and (plan_payload.get("selected_skill") or plan_payload.get("skill") or plan_payload.get("capability")):
            return plan_payload
        if session.steps:
            return None
        if session.goal:
            planner_agent = SimpleNamespace(objective=session.goal, milestones=session.metadata.get("milestones", []) or [])
            planner_output = self._planner.plan(planner_agent)
            if planner_output:
                planner_output.setdefault("goal", session.goal)
                planner_output.setdefault("objective", session.goal)
                planner_output.setdefault("selected_skill", planner_output.get("skill") or planner_output.get("capability") or "research")
                planner_output.setdefault("skill", planner_output.get("selected_skill") or "research")
                planner_output.setdefault("capability", planner_output.get("skill") or "research")
                planner_output.setdefault("action", planner_output.get("action") or "execute")
                planner_output.setdefault("confidence", 0.9)
                planner_output.setdefault("approval_required", False)
                selected_skill = planner_output.get("selected_skill") or planner_output.get("skill") or planner_output.get("capability") or "research"
                if selected_skill == "browser":
                    required_connectors = ["browser"]
                elif selected_skill == "calendar":
                    required_connectors = ["google_calendar"]
                elif selected_skill == "email":
                    required_connectors = ["gmail"]
                elif selected_skill == "document":
                    required_connectors = ["google_docs", "google_drive"]
                else:
                    required_connectors = ["browser"]
                planner_output.setdefault("required_connectors", required_connectors)
                return planner_output
            return {
                "goal": session.goal,
                "selected_skill": "research",
                "skill": "research",
                "capability": "research",
                "action": "research",
                "confidence": 0.75,
                "parameters": {"query": session.goal},
                "approval_required": False,
                "required_connectors": ["browser"],
            }
        return None

    async def _execute_step(self, step: ExecutionStep, execution_context: ExecutionContext, shared_context: SharedExecutionContext, session: ExecutionSession) -> dict[str, Any]:
        runner = self.runners.get(step.runner)
        if runner is None:
            step.status = "failed"
            step.error = f"unknown runner: {step.runner}"
            return {"status": "failed", "error": step.error, "result": None}

        attempt_count = 0
        max_retries, timeout_seconds, retry_delay_seconds = self._retry_policy(step)
        while True:
            attempt_count += 1
            step.metadata["attempt_count"] = attempt_count
            step.metadata["last_error"] = None
            step.metadata["timed_out"] = False
            if self._cancel_requested(execution_context):
                step.status = "cancelled"
                step.error = "cancelled"
                return {"status": "cancelled", "error": step.error, "result": None}
            approval_result = self.approval_engine.evaluate(
                goal=session.goal,
                action_type=step.metadata.get("action_type") or step.action,
                details=step.metadata,
            )
            step.metadata["approval_required"] = approval_result["requires_approval"]
            step.metadata["approval_reason"] = approval_result.get("reason")
            if approval_result["requires_approval"] and session.approval_decision != "approve":
                step.status = "waiting"
                step.metadata["worker_state"] = "waiting"
                step.metadata["approval_source"] = "policy"
                shared_context.approval_status = "required"
                return {
                    "status": "waiting_for_approval",
                    "output": approval_result.get("reason") or "Approval required before execution",
                    "result": {"approval": approval_result},
                }
            try:
                result = await self._execute_with_timeout(runner, step, execution_context, timeout_seconds)
            except asyncio.TimeoutError:
                step.metadata["timed_out"] = True
                message = f"step timed out after {timeout_seconds}s"
                step.error = message
                if attempt_count <= max_retries:
                    step.status = "retrying"
                    step.metadata["last_error"] = message
                    if retry_delay_seconds > 0:
                        await asyncio.sleep(retry_delay_seconds)
                    continue
                step.status = "failed"
                return {"status": "failed", "error": message, "result": None}
            except asyncio.CancelledError:
                step.status = "cancelled"
                step.error = "cancelled"
                return {"status": "cancelled", "error": step.error, "result": None}
            except Exception as exc:  # noqa: BLE001
                message = f"{type(exc).__name__}: {exc}"
                step.metadata["last_error"] = message
                if attempt_count <= max_retries:
                    step.status = "retrying"
                    if retry_delay_seconds > 0:
                        await asyncio.sleep(retry_delay_seconds)
                    continue
                step.status = "failed"
                step.error = message
                return {"status": "failed", "error": message, "result": None}

            step.status = result.get("status", "completed")
            step.output = result.get("output")
            if result.get("status") == "waiting_for_approval":
                step.status = "waiting"
                step.metadata["worker_state"] = "waiting"
                step.metadata.setdefault("approval_source", "runner")
                step.metadata["approval_required"] = True
                return {"status": "waiting_for_approval", "output": step.output, "result": result.get("result")}
            if result.get("status") == "failed":
                step.status = "failed"
                step.error = result.get("error") or "step failed"
                return {"status": "failed", "error": step.error, "result": result.get("result")}

            self._propagate_artifacts(step, result, shared_context)
            step.metadata["worker_state"] = "completed"
            return {"status": "completed", "output": step.output, "result": result.get("result")}

    async def _recover_step(self, step: ExecutionStep, execution_context: ExecutionContext, shared_context: SharedExecutionContext, session: ExecutionSession, result: dict[str, Any]) -> dict[str, Any]:
        error_text = str(result.get("error") or step.error or "")
        if not error_text:
            return {"recovered": False, "type": "none"}

        classification = self._classify_failure(error_text)
        if classification["classification"] not in {"recoverable", "needs_clarification", "needs_authentication"}:
            return {"recovered": False, "type": classification["classification"]}

        recovery_strategy = self._strategy_for(classification["classification"], error_text)
        step.metadata["recovery_strategy"] = recovery_strategy
        step.metadata["recovery_classification"] = classification["classification"]
        step.metadata["recovery_reason"] = error_text
        step.metadata["recovery_confidence"] = classification["confidence"]

        if self._should_insert_recovery_step(step, classification):
            recovery_step = ExecutionStep(
                id=f"{step.id}-recovery",
                runner=step.runner,
                action=f"recover-{step.action}",
                metadata={
                    "parent_step_id": step.id,
                    "recovery_strategy": recovery_strategy,
                    "recovery_classification": classification["classification"],
                    "retries": 1,
                },
            )
            session.steps.append(recovery_step)
            shared_context.metadata.setdefault("recovery_steps", []).append(recovery_step.id)
            shared_context.metadata.setdefault("recovery_events", []).append({"step_id": step.id, "strategy": recovery_strategy, "classification": classification["classification"]})
            session.metadata.setdefault("progress", []).append(f"Recovering from {classification['classification']}: {recovery_strategy}")
            step.status = "pending"
            step.error = None
            step.metadata["worker_state"] = "pending"
            step.metadata["last_error"] = error_text
            return {"recovered": True, "type": recovery_strategy, "recovery_step_id": recovery_step.id}

        step.status = "retrying"
        step.error = None
        step.metadata["last_error"] = error_text
        step.metadata["retries"] = max(int(step.metadata.get("retries", 0) or 0), 1)
        session.metadata.setdefault("progress", []).append(f"Retrying after {classification['classification']}: {recovery_strategy}")
        return {"recovered": True, "type": recovery_strategy}

    def _classify_failure(self, error_text: str) -> dict[str, Any]:
        lowered = error_text.casefold()
        if any(keyword in lowered for keyword in ["layout changed", "element not found", "navigation failed", "redirect", "rate limit", "timeout", "timed out", "temporarily unavailable"]):
            return {"classification": "recoverable", "confidence": 0.91, "reason": "runtime fault"}
        if any(keyword in lowered for keyword in ["authentication", "expired", "reauth"]):
            return {"classification": "needs_authentication", "confidence": 0.89, "reason": "auth issue"}
        if any(keyword in lowered for keyword in ["approval", "permission", "denied"]):
            return {"classification": "needs_approval", "confidence": 0.82, "reason": "approval or permission"}
        if any(keyword in lowered for keyword in ["conflict", "duplicate", "missing prerequisite"]):
            return {"classification": "needs_clarification", "confidence": 0.8, "reason": "context issue"}
        if any(keyword in lowered for keyword in ["unsupported", "not supported"]):
            return {"classification": "unsupported", "confidence": 0.95, "reason": "unsupported capability"}
        return {"classification": "fatal", "confidence": 0.55, "reason": "unexpected error"}

    def _strategy_for(self, classification: str, error_text: str) -> str:
        lowered = error_text.casefold()
        if classification == "needs_authentication":
            return "refresh_token"
        if classification == "needs_clarification":
            return "adjust_context"
        if "layout changed" in lowered or "element not found" in lowered or "navigation failed" in lowered:
            return "retry_browser"
        if "timeout" in lowered or "temporarily unavailable" in lowered:
            return "retry_connector"
        if "rate limit" in lowered:
            return "backoff_and_retry"
        return "retry"

    def _should_insert_recovery_step(self, step: ExecutionStep, classification: dict[str, Any]) -> bool:
        if classification["classification"] not in {"recoverable", "needs_authentication", "needs_clarification"}:
            return False
        if step.metadata.get("recovery_strategy") == "retry_browser":
            return True
        return False

    def _propagate_artifacts(self, step: ExecutionStep, result: dict[str, Any], shared_context: SharedExecutionContext) -> None:
        artifacts = result.get("artifacts") or []
        if artifacts:
            for artifact in artifacts:
                if isinstance(artifact, Artifact):
                    normalized = {"name": artifact.title, "title": artifact.title, "content": artifact.content, "artifact_type": artifact.artifact_type}
                    if not any(existing.get("name") == normalized["name"] for existing in shared_context.artifacts if isinstance(existing, dict)):
                        shared_context.artifacts.append(normalized)
                elif isinstance(artifact, dict):
                    if not any(existing.get("name") == artifact.get("name") for existing in shared_context.artifacts if isinstance(existing, dict)):
                        shared_context.artifacts.append(artifact)
                else:
                    continue
            shared_context.metadata["artifact_propagation_count"] = shared_context.metadata.get("artifact_propagation_count", 0) + len(artifacts)
        verification = result.get("verification")
        shared_context.metadata.setdefault("verification_results", [])
        if isinstance(verification, dict):
            checks = verification.get("checks")
            if isinstance(checks, list) and checks:
                shared_context.metadata["verification_results"].extend(checks)
            else:
                shared_context.metadata["verification_results"].append(verification)
            if verification.get("verified"):
                shared_context.metadata["verification_passed_count"] = shared_context.metadata.get("verification_passed_count", 0) + 1
        elif isinstance(verification, list):
            shared_context.metadata["verification_results"].extend(verification)

    def _retry_policy(self, step: ExecutionStep) -> tuple[int, float | None, float]:
        retries = step.metadata.get("retries")
        if retries is None:
            retries = step.metadata.get("retry_count")
        if retries is None:
            retries = step.metadata.get("max_retries")
        if retries is None:
            retries = 0
        timeout = step.metadata.get("timeout_seconds")
        retry_delay = step.metadata.get("retry_delay_seconds")
        return int(retries), float(timeout) if timeout is not None else None, float(retry_delay or 0)

    async def _execute_with_timeout(self, runner: StepExecutor, step: ExecutionStep, context: ExecutionContext, timeout_seconds: float | None) -> dict[str, Any]:
        if timeout_seconds is None:
            return await runner.execute(step=step, context=context)
        return await asyncio.wait_for(runner.execute(step=step, context=context), timeout=timeout_seconds)

    def _cancel_requested(self, context: ExecutionContext) -> bool:
        if context.metadata.get("cancel_requested"):
            return True
        if context.metadata.get("cancelled"):
            return True
        return False

    async def _emit_event(self, context: ExecutionContext, event_type: str, message: str, *, step: ExecutionStep | None = None, state: ExecutionState | None = None) -> None:
        event_bus = context.metadata.get("event_bus") if context.metadata else None
        event_stream = context.metadata.get("event_stream") if context.metadata else None
        event_callback = context.metadata.get("event_callback") if context.metadata else None
        if event_bus is None or not hasattr(event_bus, "publish"):
            event_bus = None
        event = {"type": event_type, "message": message}
        if step is not None:
            event["step_id"] = step.id
            event["step_status"] = step.status
            event["step_index"] = context.session.current_step_index
        if state is not None:
            event["state"] = state.value
        if event_bus is not None and event_stream:
            event_bus.publish(event_stream, event)
        if callable(event_callback):
            result = event_callback(event)
            if hasattr(result, "__await__"):
                await result

    def _shared_context(self, session: ExecutionSession, context: ExecutionContext) -> SharedExecutionContext:
        existing = context.metadata.get("shared_context") if isinstance(context.metadata, dict) else None
        if isinstance(existing, SharedExecutionContext):
            return existing
        shared = SharedExecutionContext(
            goal=session.goal,
            execution_id=session.id,
            execution_memory=session.metadata.get("execution_memory", {}),
            planner_output=session.metadata.get("planner_output"),
            clarification_answers=session.metadata.get("clarification_answers", {}),
            progress=session.metadata.get("progress", []),
            artifacts=session.metadata.get("artifacts", []),
            worker_plan=session.metadata.get("worker_plan", []),
        )
        context.metadata["shared_context"] = shared
        return shared

    def _transition_state(self, session: ExecutionSession, shared_context: SharedExecutionContext, state: ExecutionLifecycleState) -> None:
        session.metadata.setdefault("state_history", []).append(state.value)
        shared_context.metadata["state"] = state.value
        self.state_machine.transition(state=state, metadata={"execution_id": session.id, "goal": session.goal})

    def _run_cleanup_hook(self, context: ExecutionContext, step: ExecutionStep, error: str | None) -> None:
        cleanup_callback = context.metadata.get("cleanup_callback")
        if callable(cleanup_callback):
            try:
                cleanup_callback(step=step, error=error)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Execution cleanup hook failed for step %s: %s", step.id, exc)

    async def _initialize_execution_persistence(
        self,
        *,
        user_id: UUID | str,
        execution_id: str,
        workflow_type: str,
        goal: str,
        execution_context: ExecutionContext,
    ) -> None:
        """Initialize execution state, timeline, and start recording metrics."""
        if not self.persistence_service:
            return
        
        try:
            # Save initial execution state
            await self.persistence_service.save_execution_state(
                user_id=user_id,
                execution_id=execution_id,
                workflow_type=workflow_type,
                goal=goal,
                status="pending",
                current_step_index=0,
                workflow_steps=[{"id": step.id, "title": step.metadata.get("title", step.action)} for step in execution_context.session.steps],
            )
            
            # Record initial timeline event
            await self.persistence_service.record_timeline_event(
                user_id=user_id,
                execution_id=execution_id,
                phase="initialization",
                label="Execution initialized",
                status="started",
                progress=0,
            )
            
            # Store metadata for later use
            execution_context.metadata["_execution_start_time"] = datetime.utcnow()
            execution_context.metadata["_persistence_initialized"] = True
            
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to initialize execution persistence: %s", exc)

    async def _update_execution_persistence(
        self,
        *,
        user_id: UUID | str,
        execution_id: str,
        session: ExecutionSession,
        execution_context: ExecutionContext,
        phase: str,
    ) -> None:
        """Update execution state and timeline during execution."""
        if not self.persistence_service or not execution_context.metadata.get("_persistence_initialized"):
            return
        
        try:
            # Update execution state
            await self.persistence_service.save_execution_state(
                user_id=user_id,
                execution_id=execution_id,
                workflow_type=execution_context.metadata.get("workflow_type", "custom"),
                goal=session.goal,
                status=session.state.value,
                current_step_index=session.current_step_index,
                current_step_id=session.steps[session.current_step_index].id if session.current_step_index < len(session.steps) else None,
                workflow_steps=[{"id": step.id, "title": step.metadata.get("title", step.action), "status": step.status} for step in session.steps],
                clarification_answers=session.metadata.get("clarification_answers", {}),
                progress_log=session.metadata.get("progress", []),
                error_log=session.metadata.get("error_log", []),
                approval_pending=session.state == ExecutionState.WAITING_FOR_APPROVAL,
            )
            
            # Record timeline event
            progress = int((session.current_step_index / len(session.steps) * 100)) if session.steps else 0
            await self.persistence_service.record_timeline_event(
                user_id=user_id,
                execution_id=execution_id,
                phase=phase,
                label=f"Step {session.current_step_index + 1} of {len(session.steps)}",
                status=session.state.value,
                progress=progress,
            )
            
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to update execution persistence: %s", exc)

    async def _finalize_execution_persistence(
        self,
        *,
        user_id: UUID | str,
        execution_id: str,
        session: ExecutionSession,
        execution_context: ExecutionContext,
        result: ExecutionResult,
    ) -> None:
        """Finalize execution, record metrics, and store artifacts."""
        if not self.persistence_service or not execution_context.metadata.get("_persistence_initialized"):
            return
        
        try:
            # Collect artifacts from steps
            artifacts = []
            for step in session.steps:
                if step.output and isinstance(step.output, dict):
                    artifacts.append({
                        "type": step.metadata.get("artifact_type", "output"),
                        "step_id": step.id,
                        "data": step.output,
                    })
            
            # Mark execution complete
            await self.persistence_service.mark_execution_complete(
                user_id=user_id,
                execution_id=execution_id,
                status=session.state.value,
                artifacts=artifacts,
            )
            
            # Record completion timeline event
            await self.persistence_service.record_timeline_event(
                user_id=user_id,
                execution_id=execution_id,
                phase="completion",
                label="Execution completed",
                status=session.state.value,
                progress=100,
            )
            
            # Record final metrics
            start_time = execution_context.metadata.get("_execution_start_time")
            duration = (datetime.utcnow() - start_time).total_seconds() if start_time else 0
            
            retry_count = sum(step.metadata.get("attempt_count", 1) - 1 for step in session.steps)
            approval_count = sum(1 for step in session.steps if step.metadata.get("approval_required"))
            
            await self.persistence_service.record_execution_metrics(
                user_id=user_id,
                execution_id=execution_id,
                workflow_type=execution_context.metadata.get("workflow_type", "custom"),
                status=session.state.value,
                duration=duration,
                success=session.state == ExecutionState.COMPLETED,
                failure_reason=result.error,
                retry_count=retry_count,
                approval_count=approval_count,
                artifact_count=len(artifacts),
                step_count=len(session.steps),
            )
            
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to finalize execution persistence: %s", exc)
