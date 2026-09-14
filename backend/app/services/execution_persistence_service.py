from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.execution_state import ExecutionState, ExecutionMetrics, ExecutionTimeline


class ExecutionPersistenceService:
    """Persists execution state for resumable workflows and metrics tracking."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_execution_state(
        self,
        *,
        user_id: UUID,
        execution_id: str,
        workflow_type: str,
        goal: str,
        status: str,
        current_step_index: int = 0,
        current_step_id: str | None = None,
        browser_session_id: str | None = None,
        execution_context: dict[str, Any] | None = None,
        execution_session: dict[str, Any] | None = None,
        workflow_steps: list[dict[str, Any]] | None = None,
        clarification_answers: dict[str, Any] | None = None,
        progress_log: list[dict[str, Any]] | None = None,
        artifacts: list[dict[str, Any]] | None = None,
        error_log: list[dict[str, Any]] | None = None,
        approval_pending: bool = False,
        approval_data: dict[str, Any] | None = None,
    ) -> ExecutionState:
        existing = await self.session.execute(
            select(ExecutionState).where(ExecutionState.execution_id == execution_id)
        )
        state = existing.scalar_one_or_none()
        if state:
            state.status = status
            state.current_step_index = current_step_index
            state.current_step_id = current_step_id
            state.browser_session_id = browser_session_id or state.browser_session_id
            state.execution_context = execution_context or state.execution_context
            state.execution_session = execution_session or state.execution_session
            state.workflow_steps = workflow_steps or state.workflow_steps
            state.clarification_answers = clarification_answers or state.clarification_answers
            state.progress_log = progress_log or state.progress_log
            state.artifacts = artifacts or state.artifacts
            state.error_log = error_log or state.error_log
            state.approval_pending = approval_pending
            state.approval_data = approval_data or state.approval_data
            state.last_active_at = datetime.now(timezone.utc)
        else:
            state = ExecutionState(
                user_id=user_id,
                execution_id=execution_id,
                workflow_type=workflow_type,
                goal=goal,
                status=status,
                current_step_index=current_step_index,
                current_step_id=current_step_id,
                browser_session_id=browser_session_id,
                execution_context=execution_context or {},
                execution_session=execution_session or {},
                workflow_steps=workflow_steps or [],
                clarification_answers=clarification_answers or {},
                progress_log=progress_log or [],
                artifacts=artifacts or [],
                error_log=error_log or [],
                approval_pending=approval_pending,
                approval_data=approval_data or {},
                last_active_at=datetime.now(timezone.utc),
            )
            self.session.add(state)
        await self.session.flush()
        return state

    async def get_execution_state(self, *, user_id: UUID, execution_id: str) -> ExecutionState | None:
        result = await self.session.execute(
            select(ExecutionState).where(
                ExecutionState.user_id == user_id,
                ExecutionState.execution_id == execution_id,
            )
        )
        return result.scalar_one_or_none()

    async def mark_execution_complete(
        self,
        *,
        user_id: UUID,
        execution_id: str,
        status: str = "completed",
        artifacts: list[dict[str, Any]] | None = None,
    ) -> ExecutionState | None:
        state = await self.get_execution_state(user_id=user_id, execution_id=execution_id)
        if state:
            state.status = status
            state.completed_at = datetime.now(timezone.utc)
            if artifacts:
                state.artifacts = artifacts
            await self.session.flush()
        return state

    async def record_execution_metrics(
        self,
        *,
        user_id: UUID,
        execution_id: str,
        workflow_type: str,
        status: str,
        start_time: datetime,
        end_time: datetime | None = None,
        success: bool = False,
        failure_reason: str | None = None,
        retry_count: int = 0,
        browser_recoveries: int = 0,
        connector_failures: int = 0,
        approval_requests: int = 0,
        user_interventions: int = 0,
        artifacts_generated: int = 0,
        steps_completed: int = 0,
        total_steps: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionMetrics:
        end_time = end_time or datetime.now(timezone.utc)
        duration_seconds = (end_time - start_time).total_seconds() if end_time else None

        existing = await self.session.execute(
            select(ExecutionMetrics).where(ExecutionMetrics.execution_id == execution_id)
        )
        metrics = existing.scalar_one_or_none()

        if metrics:
            metrics.status = status
            metrics.end_time = end_time
            metrics.duration_seconds = duration_seconds
            metrics.success = success
            metrics.failure_reason = failure_reason
            metrics.retry_count = max(metrics.retry_count, retry_count)
            metrics.browser_recoveries = max(metrics.browser_recoveries, browser_recoveries)
            metrics.connector_failures = max(metrics.connector_failures, connector_failures)
            metrics.approval_requests = max(metrics.approval_requests, approval_requests)
            metrics.user_interventions = max(metrics.user_interventions, user_interventions)
            metrics.artifacts_generated = max(metrics.artifacts_generated, artifacts_generated)
            metrics.steps_completed = steps_completed
            metrics.total_steps = total_steps
            metrics.metadata_ = metadata or metrics.metadata_
        else:
            metrics = ExecutionMetrics(
                user_id=user_id,
                execution_id=execution_id,
                workflow_type=workflow_type,
                status=status,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration_seconds,
                success=success,
                failure_reason=failure_reason,
                retry_count=retry_count,
                browser_recoveries=browser_recoveries,
                connector_failures=connector_failures,
                approval_requests=approval_requests,
                user_interventions=user_interventions,
                artifacts_generated=artifacts_generated,
                steps_completed=steps_completed,
                total_steps=total_steps,
                metadata=metadata or {},
            )
            self.session.add(metrics)

        await self.session.flush()
        return metrics

    async def record_timeline_event(
        self,
        *,
        user_id: UUID,
        execution_id: str,
        phase: str,
        label: str,
        status: str = "completed",
        progress: int = 0,
    ) -> ExecutionTimeline:
        event = ExecutionTimeline(
            user_id=user_id,
            execution_id=execution_id,
            phase=phase,
            label=label,
            status=status,
            progress=progress,
            timestamp=datetime.now(timezone.utc),
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_execution_timeline(self, *, user_id: UUID, execution_id: str) -> list[ExecutionTimeline]:
        result = await self.session.execute(
            select(ExecutionTimeline)
            .where(
                ExecutionTimeline.user_id == user_id,
                ExecutionTimeline.execution_id == execution_id,
            )
            .order_by(ExecutionTimeline.created_at.asc())
        )
        return result.scalars().all()

    async def get_execution_metrics(self, *, user_id: UUID, execution_id: str) -> ExecutionMetrics | None:
        result = await self.session.execute(
            select(ExecutionMetrics).where(
                ExecutionMetrics.user_id == user_id,
                ExecutionMetrics.execution_id == execution_id,
            )
        )
        return result.scalar_one_or_none()
