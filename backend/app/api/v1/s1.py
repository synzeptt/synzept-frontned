from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.s1 import S1ContextOut
from app.services.s1_context_service import S1ContextService

router = APIRouter(prefix="/s1")


@router.get("/context", response_model=S1ContextOut)
async def get_s1_context(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await S1ContextService(session).get_context(user)
