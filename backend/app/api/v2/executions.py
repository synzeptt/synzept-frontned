"""Execution dashboard and timeline API endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.models.execution_state import ExecutionState, ExecutionMetrics, ExecutionTimeline
from app.services.execution_persistence_service import ExecutionPersistenceService

router = APIRouter(prefix="/executions", tags=["executions"])


@router.get("/current")
async def get_current_executions(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """List currently running executions for the user."""
    result = await session.execute(
        select(ExecutionState)
        .where(ExecutionState.user_id == user.id, ExecutionState.status.in_(["pending", "running", "waiting_for_approval"]))
        .order_by(ExecutionState.created_at.desc())
    )
    executions = result.scalars().all()
    return [
        {
            "execution_id": e.execution_id,
            "workflow_type": e.workflow_type,
            "goal": e.goal,
            "status": e.status,
            "current_step": e.current_step_id,
            "progress": e.current_step_index,
            "total_steps": len(e.workflow_steps),
            "last_active_at": e.last_active_at.isoformat() if e.last_active_at else None,
        }
        for e in executions
    ]


@router.get("/completed")
async def get_completed_executions(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    limit: int = 20,
):
    """List recently completed executions for the user."""
    result = await session.execute(
        select(ExecutionState)
        .where(ExecutionState.user_id == user.id, ExecutionState.status == "completed")
        .order_by(ExecutionState.completed_at.desc())
        .limit(limit)
    )
    executions = result.scalars().all()
    return [
        {
            "execution_id": e.execution_id,
            "workflow_type": e.workflow_type,
            "goal": e.goal,
            "status": e.status,
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            "artifacts_count": len(e.artifacts),
        }
        for e in executions
    ]


@router.get("/failed")
async def get_failed_executions(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    limit: int = 20,
):
    """List failed executions for the user."""
    result = await session.execute(
        select(ExecutionState)
        .where(ExecutionState.user_id == user.id, ExecutionState.status == "failed")
        .order_by(ExecutionState.updated_at.desc())
        .limit(limit)
    )
    executions = result.scalars().all()
    return [
        {
            "execution_id": e.execution_id,
            "workflow_type": e.workflow_type,
            "goal": e.goal,
            "status": e.status,
            "errors": e.error_log[-1] if e.error_log else None,
        }
        for e in executions
    ]


@router.get("/{execution_id}/timeline")
async def get_execution_timeline(
    execution_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get live timeline for an execution."""
    service = ExecutionPersistenceService(session)
    timeline = await service.get_execution_timeline(user_id=user.id, execution_id=execution_id)
    return [
        {
            "phase": e.phase,
            "label": e.label,
            "status": e.status,
            "progress": e.progress,
            "timestamp": e.timestamp.isoformat(),
        }
        for e in timeline
    ]


@router.get("/{execution_id}/metrics")
async def get_execution_metrics(
    execution_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get metrics for an execution."""
    service = ExecutionPersistenceService(session)
    metrics = await service.get_execution_metrics(user_id=user.id, execution_id=execution_id)
    if not metrics:
        return {}

    return {
        "execution_id": metrics.execution_id,
        "workflow_type": metrics.workflow_type,
        "status": metrics.status,
        "duration_seconds": metrics.duration_seconds,
        "success": metrics.success,
        "failure_reason": metrics.failure_reason,
        "retry_count": metrics.retry_count,
        "browser_recoveries": metrics.browser_recoveries,
        "connector_failures": metrics.connector_failures,
        "approval_requests": metrics.approval_requests,
        "user_interventions": metrics.user_interventions,
        "artifacts_generated": metrics.artifacts_generated,
        "steps_completed": metrics.steps_completed,
        "total_steps": metrics.total_steps,
    }


@router.post("/{execution_id}/resume")
async def resume_execution(
    execution_id: str,
    approval_decision: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Resume a previously interrupted execution."""
    service = ExecutionPersistenceService(session)
    
    # Verify execution exists and belongs to user
    saved_state = await service.get_execution_state(user_id=user.id, execution_id=execution_id)
    if not saved_state:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    # Return the current state and timeline (actual resume happens in background)
    timeline = await service.get_execution_timeline(user_id=user.id, execution_id=execution_id)
    metrics = await service.get_execution_metrics(user_id=user.id, execution_id=execution_id)
    
    return {
        "execution_id": execution_id,
        "status": saved_state.status,
        "current_step": saved_state.current_step_index,
        "total_steps": len(saved_state.workflow_steps),
        "goal": saved_state.goal,
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
        } if metrics else {},
    }


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get a summary of execution status for the dashboard."""
    current_result = await session.execute(
        select(ExecutionState).where(
            ExecutionState.user_id == user.id,
            ExecutionState.status.in_(["pending", "running", "waiting_for_approval"]),
        )
    )
    current_count = len(current_result.scalars().all())

    completed_result = await session.execute(
        select(ExecutionState).where(
            ExecutionState.user_id == user.id, ExecutionState.status == "completed"
        )
    )
    completed_count = len(completed_result.scalars().all())

    failed_result = await session.execute(
        select(ExecutionState).where(ExecutionState.user_id == user.id, ExecutionState.status == "failed")
    )
    failed_count = len(failed_result.scalars().all())

    return {
        "current_executions": current_count,
        "completed_executions": completed_count,
        "failed_executions": failed_count,
        "total_executions": current_count + completed_count + failed_count,
    }
