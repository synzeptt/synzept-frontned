"""Memory intelligence API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.memory.context_engine import ContextEngine
from app.memory.engine import MemoryEngine
from app.memory.pipeline import MemoryRetrievalPipeline
from app.models.user import User
from app.schemas.memory import MemoryCreate, MemoryOut

router = APIRouter(prefix="/memory")


@router.get("/context/preview")
async def preview_context(
    q: str,
    conversation_id: UUID,
    project_id: UUID | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    payload = await ContextEngine(session).build(
        user_id=user.id,
        query=q,
        conversation_id=conversation_id,
        project_id=project_id,
    )
    return {
        "intent": payload.intent.intent,
        "active_project_id": str(payload.intent.active_project_id) if payload.intent.active_project_id else None,
        "memories_count": len(payload.long_term_memories),
        "semantic_count": len(payload.semantic_snippets),
        "short_term_messages": len(payload.short_term_messages),
        "trimmed_messages": payload.trimmed_message_count,
        "long_term_memories": payload.long_term_memories,
        "semantic_snippets": payload.semantic_snippets,
    }


@router.get("/retrieve")
async def retrieve_memories(
    q: str,
    project_id: UUID | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    intent, scored, semantic = await MemoryRetrievalPipeline(session).run(user.id, q, project_id=project_id)
    return {
        "intent": intent.intent,
        "memories": [
            {"content": s.memory.content, "category": s.memory.category, "score": round(s.score, 3)}
            for s in scored
        ],
        "semantic_hits": [
            {"source_type": h.source_type, "score": round(h.score, 3), "preview": h.content[:120]}
            for h in semantic
        ],
    }


@router.post("/manual", response_model=MemoryOut)
async def create_manual_memory(
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
