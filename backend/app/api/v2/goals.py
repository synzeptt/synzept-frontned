from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.goal import (
    GoalCreate,
    GoalDashboardOut,
    GoalOut,
    GoalUpdate,
    MilestoneCreate,
    MilestoneUpdate,
    NextActionOut,
    WeeklyReviewOut,
)
from app.schemas.task import TaskCreate
from app.services.goal_progress_service import GoalProgressService

router = APIRouter(prefix="/goals")


@router.get("", response_model=list[GoalOut])
async def list_goals(
    status: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await GoalProgressService(session).list_goals(user.id, status=status)


@router.get("/dashboard", response_model=GoalDashboardOut)
async def dashboard(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GoalProgressService(session).dashboard(user.id)


@router.get("/next-actions", response_model=list[NextActionOut])
async def next_actions(
    limit: int = Query(default=5, ge=1, le=12),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await GoalProgressService(session).next_actions(user.id, limit=limit)


@router.get("/weekly-review", response_model=WeeklyReviewOut)
async def weekly_review(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GoalProgressService(session).weekly_review(user.id)


@router.get("/{goal_id}", response_model=GoalOut)
async def get_goal(
    goal_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await GoalProgressService(session).get_goal(user.id, goal_id)


@router.post("", response_model=GoalOut)
async def create_goal(
    body: GoalCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await GoalProgressService(session).create_goal(user.id, body)


@router.patch("/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: UUID,
    body: GoalUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await GoalProgressService(session).update_goal(user.id, goal_id, body)


@router.delete("/{goal_id}")
async def delete_goal(
    goal_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await GoalProgressService(session).delete_goal(user.id, goal_id)
    return {"ok": True}


@router.post("/{goal_id}/milestones", response_model=GoalOut)
async def create_milestone(
    goal_id: UUID,
    body: MilestoneCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await GoalProgressService(session).create_milestone(user.id, goal_id, body)


@router.patch("/{goal_id}/milestones/{milestone_id}", response_model=GoalOut)
async def update_milestone(
    goal_id: UUID,
    milestone_id: UUID,
    body: MilestoneUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await GoalProgressService(session).update_milestone(user.id, goal_id, milestone_id, body)


@router.post("/{goal_id}/milestones/{milestone_id}/tasks", response_model=GoalOut)
async def create_milestone_task(
    goal_id: UUID,
    milestone_id: UUID,
    body: TaskCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await GoalProgressService(session).create_task(user.id, goal_id, milestone_id, body)
