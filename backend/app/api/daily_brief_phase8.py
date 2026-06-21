from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.daily_brief_phase8 import DailyBriefOut
from app.services.daily_brief_phase8_service import DailyBriefPhase8Service

router = APIRouter(prefix="/api/daily-brief")


@router.get("/history", response_model=list[DailyBriefOut])
async def daily_brief_history(
    limit: int = Query(default=14, ge=1, le=31),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await DailyBriefPhase8Service(session).history(user.id, limit=limit)


@router.get("", response_model=DailyBriefOut)
async def get_daily_brief(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await DailyBriefPhase8Service(session).today(user.id)


@router.post("/refresh", response_model=DailyBriefOut)
async def refresh_daily_brief(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await DailyBriefPhase8Service(session).refresh(user.id)
