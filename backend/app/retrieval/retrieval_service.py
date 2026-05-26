"""Semantic memory retrieval backed by pgvector."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import bindparam, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.monitoring import monitor
from app.memory.embedding_service import EmbeddingGenerationService
from app.memory.memory_service import MemoryService
from app.models.memory import Memory
from app.retrieval.ranking_service import MemoryRankingService, RankedMemory


@dataclass(slots=True)
class RetrievalFilters:
    memory_types: list[str] | None = None
    project_id: UUID | None = None
    min_score: float = 0.35
    limit: int = 8


class SemanticRetrievalService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        embeddings: EmbeddingGenerationService | None = None,
        memory_service: MemoryService | None = None,
        ranking: MemoryRankingService | None = None,
    ) -> None:
        self.session = session
        self.embeddings = embeddings
        self.memory_service = memory_service or MemoryService(session)
        self.ranking = ranking or MemoryRankingService()

    async def retrieve(
        self,
        *,
        user_id: UUID,
        query: str,
        filters: RetrievalFilters | None = None,
    ) -> list[RankedMemory]:
        filters = filters or RetrievalFilters()
        memories = await self.memory_service.list_memories(
            user_id=user_id,
            memory_types=filters.memory_types,
            project_id=filters.project_id,
            limit=max(filters.limit * 6, 30),
        )
        semantic_scores = await self._semantic_scores(
            user_id=user_id,
            query=query,
            candidate_ids=[memory.id for memory in memories],
            limit=max(filters.limit * 4, 20),
        )
        ranked = self.ranking.rank(
            memories,
            query=query,
            semantic_scores=semantic_scores,
            project_id=filters.project_id,
            limit=filters.limit,
            min_score=filters.min_score,
        )
        await self.memory_service.mark_retrieved([item.memory for item in ranked])
        return ranked

    async def _semantic_scores(
        self,
        *,
        user_id: UUID,
        query: str,
        candidate_ids: list[UUID],
        limit: int,
    ) -> dict[UUID, float]:
        if not self.embeddings or not candidate_ids:
            return {}
        with monitor.timed("embedding.generate", source="retrieval_query"):
            vector = await self.embeddings.generate(query)
        vector_literal = "[" + ",".join(str(value) for value in vector) + "]"
        sql = text(
            """
            SELECT source_id, 1 - (embedding <=> :query_vec::vector) AS similarity
            FROM embeddings
            WHERE user_id = :user_id
              AND source_type = 'memory'
              AND source_id IN :candidate_ids
            ORDER BY embedding <=> :query_vec::vector
            LIMIT :limit
            """
        ).bindparams(bindparam("candidate_ids", expanding=True))
        with monitor.timed("retrieval.vector_query", candidate_count=len(candidate_ids), limit=limit):
            result = await self.session.execute(
                sql,
                {
                    "user_id": str(user_id),
                    "query_vec": vector_literal,
                    "candidate_ids": candidate_ids,
                    "limit": limit,
                },
            )
        return {row.source_id: float(row.similarity) for row in result}

    async def lexical_fallback(
        self,
        *,
        user_id: UUID,
        query: str,
        filters: RetrievalFilters | None = None,
    ) -> list[RankedMemory]:
        filters = filters or RetrievalFilters()
        memories = await self.memory_service.list_memories(
            user_id=user_id,
            memory_types=filters.memory_types,
            project_id=filters.project_id,
            limit=80,
        )
        return self.ranking.rank(
            memories,
            query=query,
            semantic_scores={},
            project_id=filters.project_id,
            limit=filters.limit,
            min_score=filters.min_score,
        )

    async def get_memory_by_id(self, memory_id: UUID) -> Memory | None:
        result = await self.session.execute(select(Memory).where(Memory.id == memory_id))
        return result.scalar_one_or_none()
