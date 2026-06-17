from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.memory.extraction_service import ExtractedMemory
from app.memory.memory_service import MemoryService
from app.models.user import User
from app.schemas.memory import (
    MemoryCreate,
    MemoryExplainOut,
    MemoryExplorerItemOut,
    MemoryMergeIn,
    MemoryOut,
    MemoryTrustEventOut,
    MemoryUpdate,
    UserMemoryProfile,
)
from app.services.memory_trust_service import MemoryTrustService

router = APIRouter(prefix="/memory")


@router.get("/profile", response_model=UserMemoryProfile)
async def get_user_profile(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await MemoryService(session).get_user_profile(user_id=user.id)


@router.get("", response_model=list[MemoryOut])
async def search_memory(
    q: str | None = None,
    category: str | None = None,
    limit: int = Query(default=40, ge=1, le=200),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await MemoryService(session).search_memory(user_id=user.id, query=q, category=category, limit=limit)


@router.get("/explorer", response_model=list[MemoryExplorerItemOut])
async def memory_explorer(
    include_ignored: bool = False,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await MemoryTrustService(session).explorer(user.id, include_ignored=include_ignored)


@router.get("/{memory_id}/timeline", response_model=list[MemoryTrustEventOut])
async def memory_timeline(
    memory_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await MemoryTrustService(session).timeline(user.id, memory_id)


@router.post("", response_model=MemoryOut)
async def create_memory(
    body: MemoryCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    category = body.category if body.category != "other" else body.memory_type
    item = ExtractedMemory(
        memory_type=category,
        content=body.content,
        summary=body.content,
        importance_score=body.importance,
        metadata={"source": "manual"},
        project_id=body.project_id,
    )
    return await MemoryService(session).create_memory(user_id=user.id, item=item)


@router.patch("/{memory_id}", response_model=MemoryOut)
async def update_memory(
    memory_id: UUID,
    body: MemoryUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await MemoryTrustService(session).update_memory(
        user_id=user.id,
        memory_id=memory_id,
        content=body.content,
        category=body.category,
        importance_score=body.importance,
        reason=body.reason,
    )


@router.post("/{memory_id}/merge", response_model=MemoryOut)
async def merge_memory(
    memory_id: UUID,
    body: MemoryMergeIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await MemoryTrustService(session).merge(user.id, memory_id, body.source_memory_id, reason=body.reason)


@router.post("/{memory_id}/ignore")
async def ignore_memory(
    memory_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await MemoryTrustService(session).ignore(user.id, memory_id)
    return {"ok": True}


@router.get("/explain/{message_id}", response_model=MemoryExplainOut)
async def explain_message_memory(
    message_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await MemoryTrustService(session).explain_message(user.id, message_id)


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await MemoryTrustService(session).delete(user.id, memory_id)
    return {"ok": True}
