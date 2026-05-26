"""Long-term memory: durable user knowledge with deduplication and updates."""

import hashlib
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.constants import DEDUP_SIMILARITY_THRESHOLD, MEMORY_TYPE_LONG, MEMORY_TYPE_PROJECT
from app.memory.extractor import MemoryExtractor
from app.models.memory import Memory
from app.services.embedding_service import EmbeddingService
from app.utils.text import tokenize

logger = logging.getLogger(__name__)


class LongTermMemory:
    def __init__(self, session: AsyncSession, embeddings: EmbeddingService | None = None) -> None:
        self.session = session
        self.embeddings = embeddings
        self.extractor = MemoryExtractor()

    async def process_exchange(
        self,
        *,
        user_id: UUID,
        user_message: str,
        assistant_reply: str,
        conversation_id: UUID,
        project_id: UUID | None,
    ) -> Memory | None:
        extracted = await self.extractor.extract(user_message, assistant_reply)
        if not extracted:
            return None

        memory_type = MEMORY_TYPE_PROJECT if project_id else MEMORY_TYPE_LONG
        existing = await self._find_duplicate(user_id, extracted["content"])

        if existing:
            return await self._update_memory(existing, extracted, project_id)

        memory = Memory(
            user_id=user_id,
            content=extracted["content"],
            category=extracted["category"],
            memory_type=memory_type,
            conversation_id=conversation_id,
            project_id=project_id,
            importance=extracted["importance"],
            content_hash=self._hash(extracted["content"]),
        )
        self.session.add(memory)
        await self.session.flush()
        await self._embed(memory)
        return memory

    async def _find_duplicate(self, user_id: UUID, content: str) -> Memory | None:
        content_hash = self._hash(content)
        result = await self.session.execute(
            select(Memory).where(
                Memory.user_id == user_id,
                Memory.deleted_at.is_(None),
                Memory.memory_type.in_([MEMORY_TYPE_LONG, MEMORY_TYPE_PROJECT]),
                Memory.content_hash == content_hash,
            )
        )
        exact = result.scalar_one_or_none()
        if exact:
            return exact

        # Fuzzy dedup against recent long-term memories
        result = await self.session.execute(
            select(Memory)
            .where(
                Memory.user_id == user_id,
                Memory.deleted_at.is_(None),
                Memory.memory_type.in_([MEMORY_TYPE_LONG, MEMORY_TYPE_PROJECT]),
            )
            .order_by(Memory.updated_at.desc())
            .limit(40)
        )
        new_tokens = tokenize(content)
        for memory in result.scalars().all():
            if self._similarity(new_tokens, tokenize(memory.content)) >= DEDUP_SIMILARITY_THRESHOLD:
                return memory
        return None

    async def _update_memory(self, memory: Memory, extracted: dict, project_id: UUID | None) -> Memory:
        memory.content = extracted["content"]
        memory.category = extracted["category"]
        memory.importance = max(memory.importance, extracted["importance"])
        memory.updated_at = datetime.now(timezone.utc)
        memory.content_hash = self._hash(extracted["content"])
        if project_id:
            memory.project_id = project_id
        await self.session.flush()
        await self._embed(memory)
        return memory

    async def _embed(self, memory: Memory) -> None:
        if not self.embeddings:
            return
        try:
            await self.embeddings.upsert(
                self.session,
                user_id=memory.user_id,
                source_type="memory",
                source_id=memory.id,
                content=memory.content,
            )
        except Exception as exc:
            logger.warning("Long-term embedding failed: %s", exc)

    @staticmethod
    def _hash(content: str) -> str:
        normalized = " ".join(content.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()

    @staticmethod
    def _similarity(a: set[str], b: set[str]) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)
