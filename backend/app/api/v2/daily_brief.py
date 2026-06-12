from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.daily_brief import DailyBriefOut
from app.services.daily_brief_service import DailyBriefService

router = APIRouter(prefix="/daily-brief")


@router.get("/today", response_model=DailyBriefOut)
async def get_today(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await DailyBriefService(session).get_today(user)


@router.post("/today/refresh", response_model=DailyBriefOut)
async def refresh_today(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await DailyBriefService(session).get_today(user, refresh=True)
