from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.continuity_mode import ContinuityModeOut
from app.services.continuity_mode_service import ContinuityModeService

router = APIRouter(prefix="/continuity-mode")


@router.get("", response_model=ContinuityModeOut)
async def get_continuity_mode(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ContinuityModeService(session).snapshot(user)
