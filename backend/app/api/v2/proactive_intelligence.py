from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.proactive_intelligence import (
    DailyPlanOut,
    FocusOut,
    IntelligenceItemOut,
    ProjectHealthOut,
    ProactiveOverviewOut,
    ProactiveWeeklyReviewOut,
)
from app.services.proactive_intelligence_service import ProactiveIntelligenceService

router = APIRouter(prefix="/proactive-intelligence")


@router.get("/overview", response_model=ProactiveOverviewOut)
async def get_proactive_overview(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ProactiveIntelligenceService(session).overview(user.id)


@router.post("/daily-plan", response_model=DailyPlanOut)
async def generate_daily_plan(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ProactiveIntelligenceService(session).generate_daily_plan(user.id)


@router.post("/weekly-review", response_model=ProactiveWeeklyReviewOut)
async def generate_weekly_review(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ProactiveIntelligenceService(session).generate_weekly_review(user.id)


@router.get("/project-health", response_model=list[ProjectHealthOut])
async def calculate_project_health(
    project_id: UUID | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await ProactiveIntelligenceService(session).calculate_project_health(user.id, project_id)


@router.get("/insights", response_model=list[IntelligenceItemOut])
async def generate_insights(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ProactiveIntelligenceService(session).generate_insights(user.id)


@router.get("/recommendations", response_model=list[IntelligenceItemOut])
async def recommend_next_actions(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ProactiveIntelligenceService(session).recommend_next_actions(user.id)


@router.get("/focus", response_model=FocusOut)
async def determine_focus(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ProactiveIntelligenceService(session).determine_focus(user.id)
