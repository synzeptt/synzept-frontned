from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.services.continue_engine.continue_engine_service import ContinueEngineService

router = APIRouter(prefix="/api/continue")


@router.get("", response_model=dict)
async def get_continue(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ContinueEngineService(session).get_continue(user)


@router.post("/refresh", response_model=dict)
async def post_refresh(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ContinueEngineService(session).refresh(user)
