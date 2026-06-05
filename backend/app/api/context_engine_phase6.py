from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.context_engine_phase6 import ContextSnapshotOut
from app.services.context_engine_phase6_service import ContextEnginePhase6Service

router = APIRouter(prefix="/api/context-engine")


@router.get("", response_model=ContextSnapshotOut)
async def get_context(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ContextEnginePhase6Service(session).current(user.id)


@router.post("/refresh", response_model=ContextSnapshotOut)
async def refresh_context(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ContextEnginePhase6Service(session).refresh(user.id)
