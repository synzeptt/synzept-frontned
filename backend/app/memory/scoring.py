from datetime import datetime, timezone

from app.memory.constants import (
    WEIGHT_ACCESS,
    WEIGHT_IMPORTANCE,
    WEIGHT_LEXICAL,
    WEIGHT_PROJECT,
    WEIGHT_RECENCY,
    WEIGHT_SEMANTIC,
    MIN_RELEVANCE_SCORE,
)
from app.memory.types import ScoredMemory
from app.models.memory import Memory
from app.utils.text import tokenize


def compute_recency_score(created_at: datetime) -> float:
    now = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    days = max((now - created_at).days, 0)
    return 1.0 / (1.0 + days * 0.06)


def compute_access_score(access_count: int) -> float:
    return min(access_count * 0.025, 0.25)


def compute_lexical_score(query: str, content: str) -> float:
    query_tokens = tokenize(query)
    if not query_tokens:
        return 0.0
    content_tokens = tokenize(content)
    overlap = len(query_tokens & content_tokens)
    score = overlap / len(query_tokens)
    if query.lower() in content.lower():
        score = min(score + 0.25, 1.0)
    return score


def score_memory(
    memory: Memory,
    query: str,
    *,
    semantic_score: float = 0.0,
    project_id: str | None = None,
) -> ScoredMemory:
    lexical = compute_lexical_score(query, memory.content)
    recency = compute_recency_score(memory.created_at)
    access = compute_access_score(memory.access_count)
    importance = memory.importance
    project = 1.0 if project_id and memory.project_id and str(memory.project_id) == project_id else 0.0

    composite = (
        semantic_score * WEIGHT_SEMANTIC
        + lexical * WEIGHT_LEXICAL
        + importance * WEIGHT_IMPORTANCE
        + recency * WEIGHT_RECENCY
        + access * WEIGHT_ACCESS
        + project * WEIGHT_PROJECT
    )

    return ScoredMemory(
        memory=memory,
        score=composite,
        semantic_score=semantic_score,
        lexical_score=lexical,
        recency_score=recency,
        project_score=project,
    )


def filter_relevant(scored: list[ScoredMemory], limit: int) -> list[ScoredMemory]:
    """Keep only memories above relevance threshold."""
    filtered = [s for s in scored if s.score >= MIN_RELEVANCE_SCORE]
    filtered.sort(key=lambda s: s.score, reverse=True)
    return filtered[:limit]
