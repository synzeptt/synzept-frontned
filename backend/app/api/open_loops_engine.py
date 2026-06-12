from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_pro_user
from app.models.user import User
from app.schemas.open_loops_engine import OpenLoopEngineItem, OpenLoopEngineOut
from app.services.open_loops_engine_service import OpenLoopsEngineService

router = APIRouter(prefix="/api/open-loops-engine")


@router.get("", response_model=OpenLoopEngineOut)
async def list_open_loops(user: User = Depends(require_pro_user), session: AsyncSession = Depends(get_db)):
    return await OpenLoopsEngineService(session).list(user.id)


@router.post("/{source}/{source_id}/complete", response_model=OpenLoopEngineItem)
async def complete_open_loop(
    source: str,
    source_id: UUID,
    user: User = Depends(require_pro_user),
    session: AsyncSession = Depends(get_db),
):
    return await OpenLoopsEngineService(session).complete(user.id, source, source_id)


@router.post("/{source}/{source_id}/snooze", response_model=OpenLoopEngineItem)
async def snooze_open_loop(
    source: str,
    source_id: UUID,
    user: User = Depends(require_pro_user),
    session: AsyncSession = Depends(get_db),
):
    return await OpenLoopsEngineService(session).snooze(user.id, source, source_id)


@router.post("/{source}/{source_id}/ignore", response_model=OpenLoopEngineItem)
async def ignore_open_loop(
    source: str,
    source_id: UUID,
    user: User = Depends(require_pro_user),
    session: AsyncSession = Depends(get_db),
):
    return await OpenLoopsEngineService(session).ignore(user.id, source, source_id)
