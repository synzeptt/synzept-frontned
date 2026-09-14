from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from .errors import WorkerFailureError
from .executor import StepExecutor
from .persistence import FileExecutionStore
from .types import ApprovalCheckpoint, Execution, ExecutionContext, ExecutionEvent, ExecutionState, ExecutionStep, VerificationResult

logger = logging.getLogger(__name__)


class Runtime:
    def __init__(self, *, executor_registry: dict[str, StepExecutor] | None = None, persistence: FileExecutionStore | None = None) -> None:
        self.executor_registry = executor_registry or {}
        self.persistence = persistence
        self._executions: dict[str, Execution] = {}
        self._events: dict[str, list[ExecutionEvent]] = {}
        self._transition_table = {
            ExecutionState.CREATED: {ExecutionState.PLANNING},
            ExecutionState.PLANNING: {ExecutionState.EXECUTING, ExecutionState.WAITING_FOR_INFORMATION, ExecutionState.FAILED, ExecutionState.CANCELLED},
            ExecutionState.EXECUTING: {ExecutionState.WAITING_FOR_INFORMATION, ExecutionState.WAITING_FOR_APPROVAL, ExecutionState.RETRYING, ExecutionState.VERIFYING, ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.CANCELLED},
            ExecutionState.WAITING_FOR_INFORMATION: {ExecutionState.EXECUTING, ExecutionState.CANCELLED},
            ExecutionState.WAITING_FOR_APPROVAL: {ExecutionState.EXECUTING, ExecutionState.CANCELLED},
            ExecutionState.RETRYING: {ExecutionState.EXECUTING, ExecutionState.VERIFYING, ExecutionState.FAILED, ExecutionState.CANCELLED},
            ExecutionState.VERIFYING: {ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.CANCELLED},
            ExecutionState.COMPLETED: set(),
            ExecutionState.FAILED: set(),
            ExecutionState.CANCELLED: set(),
        }

    def create_execution(self, *, goal: str, steps: list[ExecutionStep] | None = None) -> Execution:
        execution = Execution.create(goal=goal, steps=steps)
        self._executions[execution.id] = execution
        self._record_event(execution.id, "ExecutionCreated", execution.state, metadata={"goal": goal})
        self._persist(execution)
        return execution

    def get_execution(self, execution_id: str) -> Execution:
        execution = self._load(execution_id)
        if execution is None:
            raise KeyError(execution_id)
        return execution

    def start_execution(self, execution_id: str) -> Execution:
        execution = self._load_or_raise(execution_id)
        self._transition(execution, ExecutionState.PLANNING)
        self._record_event(execution.id, "ExecutionStarted", execution.state, metadata={"goal": execution.goal})
        self._persist(execution)
        return execution

    def execute_step(self, execution_id: str) -> Execution:
        execution = self._load_or_raise(execution_id)
        if execution.state not in {ExecutionState.EXECUTING, ExecutionState.PLANNING, ExecutionState.WAITING_FOR_INFORMATION, ExecutionState.RETRYING}:
            raise ValueError(f"Execution is not executable in state {execution.state}")

        if execution.current_step_index >= len(execution.steps):
            execution.state = ExecutionState.COMPLETED
            self._record_event(execution.id, "ExecutionCompleted", execution.state, metadata={"result": execution.result})
            self._persist(execution)
            return execution

        if execution.state in {ExecutionState.PLANNING, ExecutionState.WAITING_FOR_INFORMATION, ExecutionState.RETRYING}:
            self._transition(execution, ExecutionState.EXECUTING)

        step = execution.steps[execution.current_step_index]
        executor = self.executor_registry.get(step.runner)
        if executor is None:
            raise KeyError(f"Unknown runner: {step.runner}")

        retry_policy = self._retry_policy_for_step(step)
        attempt = 0
        while attempt < retry_policy.max_attempts:
            attempt += 1
            step.attempts = attempt
            step.status = "running"
            self._record_event(execution.id, "StepStarted", execution.state, step_id=step.id, metadata={"action": step.action, "attempt": attempt})
            self._persist(execution)
            try:
                result = asyncio.run(executor.execute(step=step, context=ExecutionContext(execution_id=execution.id)))
            except Exception as exc:  # noqa: BLE001
                if self._should_retry(attempt, retry_policy):
                    step.status = "retrying"
                    step.error = str(exc)
                    execution.error = str(exc)
                    self._transition(execution, ExecutionState.RETRYING)
                    self._record_event(execution.id, "RetryStarted", execution.state, step_id=step.id, metadata={"attempt": attempt, "error": str(exc)})
                    self._persist(execution)
                    continue
                step.status = "failed"
                step.error = str(exc)
                execution.error = str(exc)
                self._transition(execution, ExecutionState.FAILED)
                self._record_event(execution.id, "ExecutionFailed", execution.state, step_id=step.id, metadata={"error": str(exc)})
                self._persist(execution)
                raise WorkerFailureError(str(exc), retryable=True, metadata={"step_id": step.id}) from exc

            if result.get("status") == "waiting_for_approval":
                step.status = "waiting_for_approval"
                execution.approval = ApprovalCheckpoint(required=True, granted=False, reason="approval requested")
                self._transition(execution, ExecutionState.WAITING_FOR_APPROVAL)
                self._record_event(execution.id, "ApprovalRequested", execution.state, step_id=step.id, metadata={"reason": "approval requested"})
                self._persist(execution)
                return execution

            if result.get("status") == "failed":
                if self._should_retry(attempt, retry_policy):
                    step.status = "retrying"
                    step.error = result.get("error")
                    execution.error = result.get("error")
                    self._transition(execution, ExecutionState.RETRYING)
                    self._record_event(execution.id, "RetryStarted", execution.state, step_id=step.id, metadata={"attempt": attempt, "error": result.get("error")})
                    self._persist(execution)
                    continue
                step.status = "failed"
                step.error = result.get("error")
                execution.error = result.get("error")
                self._transition(execution, ExecutionState.FAILED)
                self._record_event(execution.id, "ExecutionFailed", execution.state, step_id=step.id, metadata={"error": result.get("error")})
                self._persist(execution)
                raise WorkerFailureError(str(result.get("error")), retryable=True, metadata={"step_id": step.id})

            step.output = result.get("output")
            step.status = "completed"
            execution.metadata["last_output"] = step.output
            execution.current_step_index += 1
            self._record_event(execution.id, "StepCompleted", execution.state, step_id=step.id, metadata={"output": step.output, "attempt": attempt})
            self._persist(execution)
            return execution

        step.status = "failed"
        self._transition(execution, ExecutionState.FAILED)
        self._record_event(execution.id, "ExecutionFailed", execution.state, step_id=step.id, metadata={"error": "max retries exceeded"})
        self._persist(execution)
        raise WorkerFailureError("max retries exceeded", retryable=True, metadata={"step_id": step.id})

    def pause_execution(self, execution_id: str, *, reason: str | None = None) -> Execution:
        execution = self._load_or_raise(execution_id)
        self._transition(execution, ExecutionState.WAITING_FOR_INFORMATION)
        execution.metadata["pause_reason"] = reason
        self._record_event(execution.id, "ExecutionPaused", execution.state, metadata={"reason": reason})
        self._persist(execution)
        return execution

    def resume_execution(self, execution_id: str) -> Execution:
        execution = self._load_or_raise(execution_id)
        self._transition(execution, ExecutionState.EXECUTING)
        self._record_event(execution.id, "ExecutionResumed", execution.state, metadata={"resume": True})
        self._persist(execution)
        return execution

    def retry_execution(self, execution_id: str) -> Execution:
        execution = self._load_or_raise(execution_id)
        self._transition(execution, ExecutionState.RETRYING)
        self._record_event(execution.id, "RetryStarted", execution.state, metadata={"step_id": execution.steps[execution.current_step_index - 1].id if execution.current_step_index > 0 else None})
        self._persist(execution)
        return execution

    def cancel_execution(self, execution_id: str) -> Execution:
        execution = self._load_or_raise(execution_id)
        self._transition(execution, ExecutionState.CANCELLED)
        execution.error = "cancelled"
        self._record_event(execution.id, "ExecutionCancelled", execution.state, metadata={"reason": "cancelled"})
        self._persist(execution)
        return execution

    def verify_execution(self, execution_id: str, *, passed: bool, details: str | None = None, evidence: dict[str, Any] | None = None) -> Execution:
        execution = self._load_or_raise(execution_id)
        self._transition(execution, ExecutionState.VERIFYING)
        execution.verification = VerificationResult(passed=passed, details=details, evidence=evidence or {})
        if passed:
            self._record_event(execution.id, "VerificationPassed", execution.state, metadata={"passed": True, "details": details})
        else:
            execution.state = ExecutionState.FAILED
            self._record_event(execution.id, "VerificationFailed", execution.state, metadata={"passed": False, "details": details})
        self._persist(execution)
        return execution

    def complete_execution(self, execution_id: str, *, result: Any | None = None) -> Execution:
        execution = self._load_or_raise(execution_id)
        if execution.state not in {ExecutionState.EXECUTING, ExecutionState.VERIFYING, ExecutionState.PLANNING}:
            raise ValueError(f"Execution cannot be completed from state {execution.state}")
        self._transition(execution, ExecutionState.COMPLETED)
        execution.result = result
        self._record_event(execution.id, "ExecutionCompleted", execution.state, metadata={"result": result})
        self._persist(execution)
        return execution

    def recover_execution(self, execution_id: str) -> Execution:
        execution = self._load_or_raise(execution_id)
        if execution.state in {ExecutionState.WAITING_FOR_INFORMATION, ExecutionState.WAITING_FOR_APPROVAL, ExecutionState.RETRYING}:
            self._record_event(execution.id, "ExecutionRecovered", execution.state, metadata={"recovered": True})
        self._persist(execution)
        return execution

    def event_history(self, execution_id: str) -> list[ExecutionEvent]:
        return list(self._events.get(execution_id, []))

    def _record_event(self, execution_id: str, event_type: str, state: ExecutionState, *, step_id: str | None = None, metadata: dict[str, Any] | None = None) -> None:
        event = ExecutionEvent(
            execution_id=execution_id,
            event_type=event_type,
            state=state,
            timestamp=datetime.now(timezone.utc).isoformat(),
            step_id=step_id,
            metadata=metadata or {},
        )
        self._events.setdefault(execution_id, []).append(event)

    def _transition(self, execution: Execution, target_state: ExecutionState) -> None:
        allowed = self._transition_table.get(execution.state, set())
        if target_state not in allowed:
            raise ValueError(f"Invalid transition from {execution.state.value} to {target_state.value}")
        execution.state = target_state

    def _retry_policy_for_step(self, step: ExecutionStep) -> Any:
        metadata = step.metadata.get("retry_policy")
        if isinstance(metadata, dict):
            return type("RetryPolicy", (), metadata)()
        if metadata is not None:
            return metadata
        return type("RetryPolicy", (), {"max_attempts": 1, "retry_delay_seconds": 0.0})()

    def _should_retry(self, attempt: int, retry_policy: Any) -> bool:
        return attempt < retry_policy.max_attempts

    def _persist(self, execution: Execution) -> None:
        if self.persistence is not None:
            self.persistence.save(execution)
        self._executions[execution.id] = execution

    def _load(self, execution_id: str) -> Execution | None:
        if execution_id in self._executions:
            return self._executions[execution_id]
        if self.persistence is not None:
            execution = self.persistence.load(execution_id)
            if execution is not None:
                self._executions[execution.id] = execution
                return execution
        return None

    def _load_or_raise(self, execution_id: str) -> Execution:
        execution = self._load(execution_id)
        if execution is None:
            raise KeyError(execution_id)
        return execution
