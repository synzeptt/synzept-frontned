from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.continuity_assistant_phase7 import ContinuityAssistantOut
from app.services.continuity_assistant_phase7_service import ContinuityAssistantPhase7Service

router = APIRouter(prefix="/api/continuity-assistant")


@router.get("", response_model=ContinuityAssistantOut)
async def get_continuity(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ContinuityAssistantPhase7Service(session).current(user.id)


@router.post("/refresh", response_model=ContinuityAssistantOut)
async def refresh_continuity(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ContinuityAssistantPhase7Service(session).refresh(user.id)
