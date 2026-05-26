"""Meaningful-only memory extraction for long-term continuity."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from uuid import UUID


MEMORY_TYPES = frozenset(
    {
        "identity",
        "goals",
        "preferences",
        "projects",
        "routines",
        "work",
        "decisions",
        "priorities",
    }
)

LOW_VALUE_PATTERNS = (
    r"^\s*(hi|hello|hey|thanks|thank you|ok|okay|yes|no|cool|nice)\s*[.!]?\s*$",
    r"^\s*(lol|haha|great|awesome)\s*[.!]?\s*$",
)


@dataclass(slots=True)
class ConversationTurn:
    role: str
    content: str


@dataclass(slots=True)
class ExtractedMemory:
    memory_type: str
    content: str
    summary: str
    importance_score: float
    metadata: dict = field(default_factory=dict)
    conversation_id: UUID | None = None
    project_id: UUID | None = None


class MemoryExtractionService:
    """Extracts durable facts without storing every chat message."""

    _rules: tuple[tuple[str, str, float], ...] = (
        ("preferences", r"\b(i prefer|i like|i dislike|i hate|my preference is|i want you to)\b", 0.72),
        ("goals", r"\b(my goal is|i want to|i need to|i'm trying to|i am trying to|goal:)\b", 0.76),
        ("identity", r"\b(i am|i'm|my name is|i work as|i live in|i'm based in)\b", 0.68),
        ("projects", r"\b(project|building|launch|roadmap|repo|app|product)\b", 0.66),
        ("routines", r"\b(every day|daily|weekly|usually|routine|each morning|each evening)\b", 0.64),
        ("work", r"\b(client|meeting|deadline|team|manager|work|job|office)\b", 0.62),
        ("decisions", r"\b(decided|decision|we chose|we picked|settled on|approved|we will|let's use|we should use)\b", 0.78),
        ("priorities", r"\b(priority|prioritize|most important|focus on|urgent|blocker)\b", 0.74),
    )

    async def extract_from_conversation(
        self,
        turns: list[ConversationTurn],
        *,
        conversation_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> list[ExtractedMemory]:
        candidates: list[ExtractedMemory] = []
        for turn in turns:
            if turn.role != "user" or self._is_low_value(turn.content):
                continue
            extracted = self._extract_turn(turn.content, conversation_id=conversation_id, project_id=project_id)
            if extracted:
                candidates.append(extracted)
        return self._dedupe_candidates(candidates)

    def _extract_turn(
        self,
        content: str,
        *,
        conversation_id: UUID | None,
        project_id: UUID | None,
    ) -> ExtractedMemory | None:
        normalized = " ".join(content.strip().split())
        if len(normalized) < 18:
            return None

        for memory_type, pattern, base_importance in self._rules:
            if re.search(pattern, normalized, flags=re.IGNORECASE):
                summary = self._summarize(normalized)
                return ExtractedMemory(
                    memory_type=memory_type,
                    content=normalized,
                    summary=summary,
                    importance_score=self._importance(normalized, base_importance),
                    metadata={"source": "conversation", "extractor": "rules_v1"},
                    conversation_id=conversation_id,
                    project_id=project_id,
                )
        return None

    @staticmethod
    def _is_low_value(content: str) -> bool:
        text = content.strip()
        if len(text) < 12:
            return True
        return any(re.match(pattern, text, flags=re.IGNORECASE) for pattern in LOW_VALUE_PATTERNS)

    @staticmethod
    def _summarize(content: str) -> str:
        if len(content) <= 180:
            return content
        return content[:177].rsplit(" ", 1)[0] + "..."

    @staticmethod
    def _importance(content: str, base: float) -> float:
        boosters = ("always", "never", "important", "critical", "must", "deadline", "priority")
        score = base + sum(0.04 for token in boosters if token in content.lower())
        return min(score, 0.95)

    @staticmethod
    def _dedupe_candidates(candidates: list[ExtractedMemory]) -> list[ExtractedMemory]:
        seen: set[str] = set()
        unique: list[ExtractedMemory] = []
        for candidate in candidates:
            key = re.sub(r"\W+", " ", candidate.content.lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
        return unique
