from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.exceptions import NotFoundError
from app.memory.engine import MemoryEngine
from app.models.memory import Memory
from app.models.user import User
from app.schemas.feedback import MemoryFeedbackCreate, UsageEventCreate
from app.schemas.memory import MemoryCreate, MemoryOut, MemoryUpdate
from app.api.v1.feedback import create_memory_feedback, create_usage_event

router = APIRouter(prefix="/memories")


@router.get("", response_model=list[MemoryOut])
async def list_memories(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    engine = MemoryEngine(session)
    return await engine.store.list_for_user(user.id, limit=40)


@router.post("", response_model=MemoryOut)
async def create_memory(
    body: MemoryCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    engine = MemoryEngine(session)
    return await engine.store.create(
        user_id=user.id,
        content=body.content,
        category=body.category,
        memory_type=body.memory_type,
        project_id=body.project_id,
        importance=body.importance,
    )


@router.patch("/{memory_id}", response_model=MemoryOut)
async def update_memory(
    memory_id: UUID,
    body: MemoryUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(Memory).where(Memory.id == memory_id, Memory.user_id == user.id))
    memory = result.scalar_one_or_none()
    if not memory:
        raise NotFoundError("Memory not found")
    if body.content is not None:
        memory.content = body.content
    if body.category is not None:
        memory.category = body.category
    if body.importance is not None:
        memory.importance = body.importance
    await create_memory_feedback(
        MemoryFeedbackCreate(memory_id=memory.id, signal="edited", corrected_context=memory.content),
        user,
        session,
    )
    await create_usage_event(UsageEventCreate(event_type="memory_edited", surface="memories"), user, session)
    return memory


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(Memory).where(Memory.id == memory_id, Memory.user_id == user.id))
    memory = result.scalar_one_or_none()
    if not memory:
        raise NotFoundError("Memory not found")
    await session.delete(memory)
    await create_memory_feedback(MemoryFeedbackCreate(memory_id=memory.id, signal="removed"), user, session)
    await create_usage_event(UsageEventCreate(event_type="memory_removed", surface="memories"), user, session)
    return {"ok": True}
