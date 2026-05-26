"""Long-term memory persistence and async post-response processing."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.jobs import JobType, enqueue
from app.memory.embedding_service import EmbeddingGenerationService
from app.memory.extraction_service import ConversationTurn, ExtractedMemory, MemoryExtractionService, MEMORY_TYPES
from app.models.memory import Memory


class MemoryService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        extractor: MemoryExtractionService | None = None,
        embeddings: EmbeddingGenerationService | None = None,
    ) -> None:
        self.session = session
        self.extractor = extractor or MemoryExtractionService()
        self.embeddings = embeddings

    def enqueue_post_response_processing(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        user_message: str,
        assistant_reply: str,
        project_id: UUID | None = None,
    ) -> None:
        enqueue(
            JobType.MEMORY_POST_RESPONSE,
            user_id=user_id,
            conversation_id=conversation_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
            project_id=project_id,
        )

    async def process_conversation(
        self,
        *,
        user_id: UUID,
        turns: list[ConversationTurn],
        conversation_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> list[Memory]:
        extracted = await self.extractor.extract_from_conversation(
            turns,
            conversation_id=conversation_id,
            project_id=project_id,
        )
        memories: list[Memory] = []
        for item in extracted:
            if await self._near_duplicate_exists(user_id=user_id, item=item):
                continue
            memory = await self.create_memory(user_id=user_id, item=item)
            memories.append(memory)
        return memories

    async def create_memory(self, *, user_id: UUID, item: ExtractedMemory) -> Memory:
        memory_type = item.memory_type if item.memory_type in MEMORY_TYPES else "work"
        memory = Memory(
            user_id=user_id,
            conversation_id=item.conversation_id,
            project_id=item.project_id,
            memory_type=memory_type,
            category=memory_type,
            content=item.content,
            summary=item.summary,
            importance_score=item.importance_score,
            recency_score=1.0,
            retrieval_count=0,
            metadata_=item.metadata,
            content_hash=self._content_hash(item.content),
        )
        self.session.add(memory)
        await self.session.flush()

        if self.embeddings:
            embedding = await self.embeddings.upsert_embedding(
                self.session,
                user_id=user_id,
                source_type="memory",
                source_id=memory.id,
                content=f"{memory.summary or memory.content}\n{memory.content}",
                metadata={"memory_type": memory.memory_type},
            )
            memory.embedding_id = embedding.id
        return memory

    async def list_memories(
        self,
        *,
        user_id: UUID,
        memory_types: list[str] | None = None,
        project_id: UUID | None = None,
        limit: int = 80,
    ) -> list[Memory]:
        query: Select[tuple[Memory]] = select(Memory).where(Memory.user_id == user_id, Memory.deleted_at.is_(None))
        if memory_types:
            query = query.where(Memory.memory_type.in_(memory_types))
        if project_id:
            query = query.where((Memory.project_id == project_id) | (Memory.project_id.is_(None)))
        query = query.order_by(Memory.importance_score.desc(), Memory.updated_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_retrieved(self, memories: list[Memory]) -> None:
        now = datetime.now(timezone.utc)
        for memory in memories:
            memory.retrieval_count += 1
            memory.last_accessed_at = now

    async def _near_duplicate_exists(self, *, user_id: UUID, item: ExtractedMemory) -> bool:
        result = await self.session.execute(
            select(Memory.id).where(
                Memory.user_id == user_id,
                Memory.content_hash == self._content_hash(item.content),
                Memory.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    def _content_hash(content: str) -> str:
        normalized = " ".join(content.lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
