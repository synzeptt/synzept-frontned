from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.home import HomeOut
from app.services.home_intelligence_service import HomeIntelligenceService

router = APIRouter(prefix="/api/home")


@router.get("", response_model=HomeOut)
async def get_home(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await HomeIntelligenceService(session).get_home(user)


@router.post("/refresh", response_model=HomeOut)
async def refresh_home(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await HomeIntelligenceService(session).refresh_home(user)
