from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.autonomous_workspace import (
    AutonomousSuggestionOut,
    AutonomousWorkspaceOut,
    ExecutionStateOut,
    GoalPlanRequest,
    GoalPlanOut,
    GoalProgressEstimateOut,
    WeeklyPlanOut,
)
from app.schemas.proactive_intelligence import ProjectHealthOut
from app.services.autonomous_workspace_service import AutonomousWorkspaceService
from app.services.proactive_intelligence_service import ProactiveIntelligenceService

router = APIRouter(prefix="/autonomous-workspace")


@router.get("", response_model=AutonomousWorkspaceOut)
async def overview(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await AutonomousWorkspaceService(session).overview(user.id)


@router.post("/goal-plan", response_model=GoalPlanOut)
async def goal_plan(body: GoalPlanRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await AutonomousWorkspaceService(session).goal_to_plan(user.id, body.goal_id, create_structure=body.create_structure)


@router.get("/project-health", response_model=list[ProjectHealthOut])
async def project_health(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ProactiveIntelligenceService(session).calculate_project_health(user.id)


@router.get("/execution", response_model=ExecutionStateOut)
async def execution(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await AutonomousWorkspaceService(session).execution_state(user.id)


@router.get("/goals/{goal_id}/progress", response_model=GoalProgressEstimateOut)
async def goal_progress(goal_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await AutonomousWorkspaceService(session).goal_progress_estimate(user.id, goal_id)


@router.get("/weekly-plan", response_model=WeeklyPlanOut)
async def weekly_plan(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await AutonomousWorkspaceService(session).weekly_plan(user.id)


@router.post("/suggestions/generate", response_model=list[AutonomousSuggestionOut])
async def generate_suggestions(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await AutonomousWorkspaceService(session).generate_suggestions(user.id)
