from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.continue_context import ContinueContextOut
from app.services.continue_context_service import ContinueContextService

router = APIRouter(prefix="/continue")


@router.get("/context", response_model=ContinueContextOut)
async def get_continue_context(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ContinueContextService(session).get_context(user)
