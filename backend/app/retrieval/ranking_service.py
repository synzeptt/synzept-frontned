"""Modular memory ranking for continuity-oriented retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.models.memory import Memory
from app.utils.text import tokenize


@dataclass(slots=True)
class RankedMemory:
    memory: Memory
    score: float
    semantic_score: float
    recency_score: float
    importance_score: float
    retrieval_frequency_score: float
    project_score: float


class MemoryRankingService:
    def __init__(
        self,
        *,
        semantic_weight: float = 0.48,
        recency_weight: float = 0.14,
        importance_weight: float = 0.22,
        retrieval_weight: float = 0.03,
        project_weight: float = 0.13,
    ) -> None:
        self.semantic_weight = semantic_weight
        self.recency_weight = recency_weight
        self.importance_weight = importance_weight
        self.retrieval_weight = retrieval_weight
        self.project_weight = project_weight

    def rank(
        self,
        memories: list[Memory],
        *,
        query: str,
        semantic_scores: dict[UUID, float],
        project_id: UUID | None = None,
        limit: int = 8,
        min_score: float = 0.35,
    ) -> list[RankedMemory]:
        ranked = [
            self.score_memory(memory, query=query, semantic_score=semantic_scores.get(memory.id, 0.0), project_id=project_id)
            for memory in memories
        ]
        selected = [item for item in ranked if item.score >= min_score]
        selected.sort(key=lambda item: item.score, reverse=True)
        return selected[:limit]

    def score_memory(
        self,
        memory: Memory,
        *,
        query: str,
        semantic_score: float,
        project_id: UUID | None = None,
    ) -> RankedMemory:
        semantic = max(semantic_score, self._lexical_similarity(query, memory.content) * 0.7)
        recency = self._recency(memory.created_at)
        importance = min(max(memory.importance_score, 0.0), 1.0)
        retrieval = min(memory.retrieval_count * 0.01, 0.08)
        project = 1.0 if project_id and memory.project_id == project_id else 0.0
        if project_id and memory.project_id is None:
            project = 0.2

        score = (
            semantic * self.semantic_weight
            + recency * self.recency_weight
            + importance * self.importance_weight
            + retrieval * self.retrieval_weight
            + project * self.project_weight
        )
        return RankedMemory(
            memory=memory,
            score=score,
            semantic_score=semantic,
            recency_score=recency,
            importance_score=importance,
            retrieval_frequency_score=retrieval,
            project_score=project,
        )

    @staticmethod
    def _recency(created_at: datetime) -> float:
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_days = max((datetime.now(timezone.utc) - created_at).days, 0)
        return 1.0 / (1.0 + age_days * 0.04)

    @staticmethod
    def _lexical_similarity(query: str, content: str) -> float:
        query_tokens = tokenize(query)
        if not query_tokens:
            return 0.0
        content_tokens = tokenize(content)
        return len(query_tokens & content_tokens) / len(query_tokens)
