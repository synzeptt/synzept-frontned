"""Memory validation and context filtering safeguards."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.memory.constants import MIN_RELEVANCE_SCORE, MIN_SEMANTIC_SCORE
from app.utils.text import tokenize, truncate

if TYPE_CHECKING:
    from app.memory.types import ScoredMemory, SemanticHit

logger = logging.getLogger("synzept.memory")


@dataclass(frozen=True)
class RetrievalDiagnostics:
    candidates: int
    selected: int
    semantic_hits: int
    filtered_low_score: int
    filtered_untrusted: int


UNTRUSTED_MEMORY_PATTERNS = (
    re.compile(r"\bignore (previous|prior|above) instructions\b", re.I),
    re.compile(r"\breveal (system|developer) prompt\b", re.I),
)


def is_memory_trusted(content: str) -> bool:
    if len(content.strip()) < 12:
        return False
    return not any(pattern.search(content) for pattern in UNTRUSTED_MEMORY_PATTERNS)


def has_query_anchor(query: str, content: str) -> bool:
    query_tokens = tokenize(query)
    if not query_tokens:
        return True
    content_tokens = tokenize(content)
    return bool(query_tokens & content_tokens)


def filter_scored_memories(
    scored: list["ScoredMemory"],
    *,
    query: str,
    limit: int,
    min_score: float = MIN_RELEVANCE_SCORE,
) -> tuple[list["ScoredMemory"], RetrievalDiagnostics]:
    selected: list["ScoredMemory"] = []
    low_score = 0
    untrusted = 0

    for item in sorted(scored, key=lambda s: s.score, reverse=True):
        if item.score < min_score:
            low_score += 1
            continue
        if not is_memory_trusted(item.memory.content):
            untrusted += 1
            continue
        if item.semantic_score < MIN_SEMANTIC_SCORE and item.lexical_score < 0.12 and not has_query_anchor(query, item.memory.content):
            low_score += 1
            continue
        selected.append(item)
        if len(selected) >= limit:
            break

    diagnostics = RetrievalDiagnostics(
        candidates=len(scored),
        selected=len(selected),
        semantic_hits=0,
        filtered_low_score=low_score,
        filtered_untrusted=untrusted,
    )
    return selected, diagnostics


def filter_semantic_hits(hits: list["SemanticHit"], *, query: str, limit: int) -> list["SemanticHit"]:
    trusted: list["SemanticHit"] = []
    for hit in hits:
        if hit.score < MIN_SEMANTIC_SCORE or not is_memory_trusted(hit.content):
            continue
        if not has_query_anchor(query, hit.content) and hit.score < 0.52:
            continue
        if len(hit.content) > 700:
            trusted.append(hit.__class__(hit.source_type, hit.source_id, truncate(hit.content, 700), hit.score))
        else:
            trusted.append(hit)
        if len(trusted) >= limit:
            break
    return trusted
