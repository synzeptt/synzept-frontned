from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.daily.operating import DailyOperatingService
from app.models.user import User

router = APIRouter(prefix="/briefing")


@router.get("")
async def daily_briefing(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    row = await DailyOperatingService(session).ensure_morning_briefing(user)
    return {"briefing": row.summary}
