"""Long-term memory persistence and async post-response processing."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.jobs import JobType, enqueue
from app.memory.embedding_service import EmbeddingGenerationService
from app.memory.extraction_service import ConversationTurn, ExtractedMemory, MemoryExtractionService, MEMORY_TYPES
from app.core.exceptions import NotFoundError
from app.models.memory import Memory, MemoryRevision, MemoryTrustEvent
from app.models.user import User


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
            existing = await self._find_duplicate(user_id=user_id, item=item)
            memory = (
                await self._merge_memory(existing, item)
                if existing
                else await self.create_memory(user_id=user_id, item=item)
            )
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
            version=1,
            metadata_=item.metadata,
            content_hash=self._content_hash(item.content),
        )
        self.session.add(memory)
        await self.session.flush()
        await self._record_revision(memory, action="created")
        await self._record_trust_event(memory, action="created", reason="Synzept created this memory from conversation context.", caused_by_type="conversation", caused_by_id=item.conversation_id)

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

    async def update_memory(
        self,
        *,
        user_id: UUID,
        memory_id: UUID,
        content: str | None = None,
        category: str | None = None,
        importance_score: float | None = None,
        pinned: bool | None = None,
        archived: bool | None = None,
        include_archived: bool = False,
    ) -> Memory:
        memory = await self._get_owned(user_id=user_id, memory_id=memory_id, include_archived=include_archived)
        if content is not None:
            memory.content = content
            memory.summary = self.extractor._summarize(content)
            memory.content_hash = self._content_hash(content)
        if category is not None:
            memory.category = category
            memory.memory_type = category if category in MEMORY_TYPES else memory.memory_type
        if importance_score is not None:
            memory.importance_score = importance_score
        if pinned is not None:
            memory.pinned = pinned
        if archived is not None:
            memory.archived_at = datetime.now(timezone.utc) if archived else None
        memory.version += 1
        await self.session.flush()
        await self._record_revision(memory, action="updated")
        await self._record_trust_event(memory, action="edited", reason="Memory was edited by the user.", caused_by_type="user")
        return memory

    async def delete_memory(self, *, user_id: UUID, memory_id: UUID) -> None:
        memory = await self._get_owned(user_id=user_id, memory_id=memory_id)
        memory.version += 1
        memory.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self._record_revision(memory, action="deleted")
        await self._record_trust_event(memory, action="deleted", reason="Memory was deleted by the user.", caused_by_type="user")

    async def search_memory(
        self,
        *,
        user_id: UUID,
        query: str | None = None,
        category: str | None = None,
        limit: int = 40,
    ) -> list[Memory]:
        statement = select(Memory).where(Memory.user_id == user_id, Memory.deleted_at.is_(None), Memory.archived_at.is_(None))
        if category:
            statement = statement.where(Memory.category == category)
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(or_(Memory.content.ilike(pattern), Memory.summary.ilike(pattern)))
        result = await self.session.execute(
            statement.order_by(Memory.pinned.desc(), Memory.importance_score.desc(), Memory.updated_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_profile(self, *, user_id: UUID) -> dict:
        user = await self.session.get(User, user_id)
        memories = await self.search_memory(user_id=user_id, limit=200)
        grouped = {key: [] for key in ("goals", "projects", "interests", "skills", "long_term_plans")}
        for memory in memories:
            if memory.category in grouped and memory.content not in grouped[memory.category]:
                grouped[memory.category].append(memory.content)
        return {
            "userId": str(user_id),
            **grouped,
            "preferences": user.preferences or {} if user else {},
            "memories": memories,
        }

    async def list_memories(
        self,
        *,
        user_id: UUID,
        memory_types: list[str] | None = None,
        project_id: UUID | None = None,
        limit: int = 80,
    ) -> list[Memory]:
        query: Select[tuple[Memory]] = select(Memory).where(Memory.user_id == user_id, Memory.deleted_at.is_(None), Memory.archived_at.is_(None))
        if memory_types:
            query = query.where(Memory.memory_type.in_(memory_types))
        if project_id:
            query = query.where((Memory.project_id == project_id) | (Memory.project_id.is_(None)))
        query = query.order_by(Memory.pinned.desc(), Memory.importance_score.desc(), Memory.updated_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_retrieved(self, memories: list[Memory]) -> None:
        now = datetime.now(timezone.utc)
        for memory in memories:
            memory.retrieval_count += 1
            memory.last_accessed_at = now

    async def _find_duplicate(self, *, user_id: UUID, item: ExtractedMemory) -> Memory | None:
        result = await self.session.execute(
            select(Memory).where(
                Memory.user_id == user_id,
                Memory.content_hash == self._content_hash(item.content),
                Memory.category == item.memory_type,
                Memory.deleted_at.is_(None),
                Memory.archived_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def _merge_memory(self, memory: Memory, item: ExtractedMemory) -> Memory:
        metadata = dict(memory.metadata_ or {})
        metadata["occurrences"] = int(metadata.get("occurrences", 1)) + 1
        memory.metadata_ = metadata
        memory.importance_score = max(memory.importance_score, item.importance_score)
        memory.conversation_id = item.conversation_id or memory.conversation_id
        memory.project_id = item.project_id or memory.project_id
        memory.version += 1
        await self.session.flush()
        await self._record_revision(memory, action="merged")
        await self._record_trust_event(memory, action="merged", reason="Synzept merged a repeated memory signal.", caused_by_type="conversation", caused_by_id=item.conversation_id)
        return memory

    async def _get_owned(self, *, user_id: UUID, memory_id: UUID, include_archived: bool = False) -> Memory:
        statement = select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id, Memory.deleted_at.is_(None))
        if not include_archived:
            statement = statement.where(Memory.archived_at.is_(None))
        result = await self.session.execute(statement)
        memory = result.scalar_one_or_none()
        if not memory:
            raise NotFoundError("Memory not found")
        return memory

    async def _record_revision(self, memory: Memory, *, action: str) -> None:
        self.session.add(
            MemoryRevision(
                memory_id=memory.id,
                user_id=memory.user_id,
                version=memory.version,
                action=action,
                content=memory.content,
                category=memory.category or memory.memory_type,
                importance_score=memory.importance_score,
                metadata_=dict(memory.metadata_ or {}),
            )
        )
        await self.session.flush()

    async def _record_trust_event(
        self,
        memory: Memory,
        *,
        action: str,
        reason: str,
        caused_by_type: str,
        caused_by_id: UUID | None = None,
    ) -> None:
        self.session.add(
            MemoryTrustEvent(
                memory_id=memory.id,
                user_id=memory.user_id,
                action=action,
                reason=reason,
                caused_by_type=caused_by_type,
                caused_by_id=caused_by_id,
                before={},
                after={
                    "content": memory.content,
                    "category": memory.category,
                    "importance": memory.importance_score,
                    "confidence": memory.confidence,
                },
                metadata_=dict(memory.metadata_ or {}),
            )
        )
        await self.session.flush()

    @staticmethod
    def _content_hash(content: str) -> str:
        normalized = " ".join(content.lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
