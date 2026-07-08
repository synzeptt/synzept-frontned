from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.services.daily_brief_phase8_service import DailyBriefPhase8Service

router = APIRouter(prefix="/api/daily")


@router.get("", response_model=dict)
async def get_daily(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await DailyBriefPhase8Service(session).today(user.id)


@router.post("/refresh", response_model=dict)
async def refresh_daily(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await DailyBriefPhase8Service(session).refresh(user.id)
