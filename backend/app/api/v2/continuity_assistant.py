from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.continuity_assistant import ContinuityAssistantOut
from app.services.continuity_assistant_service import ContinuityAssistantService

router = APIRouter(prefix="/continuity-assistant")


@router.get("/overview", response_model=ContinuityAssistantOut)
async def get_overview(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ContinuityAssistantService(session).overview(user)
