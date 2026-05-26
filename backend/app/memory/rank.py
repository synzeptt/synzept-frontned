from app.memory.scoring import filter_relevant, score_memory
from app.models.memory import Memory


def rank_memories(memories: list[Memory], query: str, semantic_scores: dict[str, float] | None = None) -> list[Memory]:
    scored = [
        score_memory(m, query, semantic_score=(semantic_scores or {}).get(str(m.id), 0.0))
        for m in memories
        if not m.deleted_at
    ]
    return [s.memory for s in filter_relevant(scored, len(memories))]
