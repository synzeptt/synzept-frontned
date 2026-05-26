import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.constants import MEMORY_TYPE_LONG, MEMORY_TYPE_PROJECT
from app.models.memory import Memory
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class MemoryStore:
    def __init__(self, session: AsyncSession, embeddings: EmbeddingService | None = None) -> None:
        self.session = session
        self.embeddings = embeddings

    async def create(
        self,
        *,
        user_id: UUID,
        content: str,
        category: str = "other",
        memory_type: str = "long_term",
        conversation_id: UUID | None = None,
        project_id: UUID | None = None,
        importance: float = 0.6,
    ) -> Memory:
        import hashlib

        memory = Memory(
            user_id=user_id,
            content=content,
            category=category,
            memory_type=memory_type,
            conversation_id=conversation_id,
            project_id=project_id,
            importance=importance,
            content_hash=hashlib.sha256(" ".join(content.lower().split()).encode()).hexdigest(),
        )
        self.session.add(memory)
        await self.session.flush()
        if self.embeddings and memory_type in ("long_term", "project"):
            try:
                await self.embeddings.upsert(
                    self.session,
                    user_id=user_id,
                    source_type="memory",
                    source_id=memory.id,
                    content=content,
                )
            except Exception as exc:
                logger.warning("Memory embedding failed: %s", exc)
        return memory

    async def list_long_term(
        self,
        user_id: UUID,
        *,
        project_id: UUID | None = None,
        limit: int = 80,
    ) -> list[Memory]:
        query = select(Memory).where(
            Memory.user_id == user_id,
            Memory.deleted_at.is_(None),
            Memory.memory_type.in_([MEMORY_TYPE_LONG, MEMORY_TYPE_PROJECT]),
        )
        if project_id:
            query = query.where(
                (Memory.project_id == project_id) | (Memory.project_id.is_(None))
            )
        result = await self.session.execute(query.order_by(Memory.importance_score.desc()).limit(limit))
        return list(result.scalars().all())

    async def list_for_user(self, user_id: UUID, memory_type: str | None = None, limit: int = 50) -> list[Memory]:
        query = select(Memory).where(Memory.user_id == user_id, Memory.deleted_at.is_(None))
        if memory_type:
            query = query.where(Memory.memory_type == memory_type)
        result = await self.session.execute(query.order_by(Memory.created_at.desc()).limit(limit))
        return list(result.scalars().all())

    async def touch_accessed(self, memories: list[Memory]) -> None:
        now = datetime.now(timezone.utc)
        for memory in memories:
            memory.access_count += 1
            memory.last_accessed_at = now
