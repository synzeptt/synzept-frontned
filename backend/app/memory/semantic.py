"""Semantic memory retrieval via pgvector."""

import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.constants import MAX_SEMANTIC_HITS, MIN_SEMANTIC_SCORE
from app.memory.types import SemanticHit
from app.services.embedding_service import EmbeddingService
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SemanticRetriever:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._embeddings: EmbeddingService | None = None
        if get_settings().is_sqlite:
            return
        try:
            self._embeddings = EmbeddingService()
        except ValueError:
            pass

    async def search(self, user_id: UUID, query: str, limit: int = MAX_SEMANTIC_HITS) -> list[SemanticHit]:
        if not self._embeddings:
            return []
        try:
            vector = await self._embeddings.embed(query)
            vector_literal = "[" + ",".join(str(v) for v in vector) + "]"
            sql = text(
                """
                SELECT source_type, source_id::text, content,
                       1 - (embedding <=> :query_vec::vector) AS score
                FROM embeddings
                WHERE user_id = :user_id
                ORDER BY embedding <=> :query_vec::vector
                LIMIT :limit
                """
            )
            result = await self.session.execute(
                sql,
                {"user_id": str(user_id), "query_vec": vector_literal, "limit": limit * 2},
            )
            hits: list[SemanticHit] = []
            for row in result:
                score = float(row.score)
                if score < MIN_SEMANTIC_SCORE:
                    continue
                hits.append(
                    SemanticHit(
                        source_type=row.source_type,
                        source_id=UUID(row.source_id),
                        content=row.content,
                        score=score,
                    )
                )
                if len(hits) >= limit:
                    break
            logger.info(
                "semantic retrieval",
                extra={"user_id": str(user_id), "hit_count": len(hits), "limit": limit},
            )
            return hits
        except Exception as exc:
            logger.warning("Semantic search failed: %s", exc)
            return []

    def build_semantic_score_map(
        self, hits: list[SemanticHit], memory_ids: list[UUID]
    ) -> dict[str, float]:
        """Map memory IDs to best semantic score from embedding hits."""
        id_set = {str(mid) for mid in memory_ids}
        scores: dict[str, float] = {}
        for hit in hits:
            if hit.source_type == "memory" and str(hit.source_id) in id_set:
                key = str(hit.source_id)
                scores[key] = max(scores.get(key, 0.0), hit.score)
        return scores
