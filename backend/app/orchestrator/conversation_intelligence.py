"""Conversation continuity intelligence for cross-session context."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.memory import Memory
from app.utils.text import tokenize, truncate


DECISION_PATTERNS = (
    r"\b(decided|decision|we chose|we picked|settled on|approved|we will|let's use|we should use)\b",
)
OPEN_LOOP_PATTERNS = (
    r"\b(still need|need to|todo|to-do|next step|follow up|unresolved|open question|not decided|blocked)\b",
)
TOPIC_STOPWORDS = {
    "continue",
    "resume",
    "about",
    "through",
    "should",
    "would",
    "could",
    "there",
    "their",
    "synzept",
}


@dataclass(slots=True)
class ConversationContinuityState:
    topics: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    open_loops: list[str] = field(default_factory=list)
    summary: str = ""


class ConversationIntelligenceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def update_after_turn(
        self,
        *,
        conversation: Conversation,
        user_message: str,
        assistant_reply: str,
        project_id: UUID | None = None,
    ) -> ConversationContinuityState:
        state = self.extract_state(user_message=user_message, assistant_reply=assistant_reply)
        previous = conversation.summary or ""
        conversation.summary = self.merge_summary(previous, state)
        conversation.active_intent = self.active_intent(state)
        if project_id and not conversation.project_id:
            conversation.project_id = project_id
        return state

    async def related_context(
        self,
        *,
        user_id: UUID,
        query: str,
        current_conversation_id: UUID | None = None,
        project_id: UUID | None = None,
        limit: int = 6,
    ) -> list[str]:
        query_tokens = {token for token in tokenize(query) if len(token) > 3}
        lines: list[tuple[float, str]] = []

        conversation_query = select(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.deleted_at.is_(None),
            Conversation.archived_at.is_(None),
        )
        if current_conversation_id:
            conversation_query = conversation_query.where(Conversation.id != current_conversation_id)
        if project_id:
            conversation_query = conversation_query.where(
                (Conversation.project_id == project_id) | (Conversation.project_id.is_(None))
            )
        result = await self.session.execute(conversation_query.order_by(Conversation.updated_at.desc()).limit(12))
        for conversation in result.scalars().all():
            text = " ".join(part for part in [conversation.title or "", conversation.summary or "", conversation.active_intent or ""] if part)
            score = self._relevance(query_tokens, text)
            if score <= 0 and not project_id:
                continue
            detail = truncate(conversation.summary or conversation.active_intent or "", 240)
            if detail:
                lines.append((score + 0.12, f"Related discussion: {conversation.title or 'Untitled conversation'} - {detail}"))

        memory_query = select(Memory).where(
            Memory.user_id == user_id,
            Memory.deleted_at.is_(None),
            Memory.memory_type.in_(["decisions", "priorities", "projects", "goals", "preferences"]),
        )
        if project_id:
            memory_query = memory_query.where((Memory.project_id == project_id) | (Memory.project_id.is_(None)))
        memory_result = await self.session.execute(memory_query.order_by(Memory.importance_score.desc(), Memory.updated_at.desc()).limit(16))
        for memory in memory_result.scalars().all():
            text = f"{memory.memory_type} {memory.summary or ''} {memory.content}"
            score = self._relevance(query_tokens, text) + memory.importance_score * 0.18
            if score < 0.12:
                continue
            label = "Decision" if memory.memory_type == "decisions" else "Continuity memory"
            lines.append((score, f"{label}: {truncate(memory.summary or memory.content, 240)}"))

        lines.sort(key=lambda item: item[0], reverse=True)
        seen: set[str] = set()
        selected: list[str] = []
        for _, line in lines:
            if line in seen:
                continue
            seen.add(line)
            selected.append(line)
            if len(selected) >= limit:
                break
        return selected

    @classmethod
    def extract_state(cls, *, user_message: str, assistant_reply: str) -> ConversationContinuityState:
        combined = f"{user_message}\n{assistant_reply}"
        topics = cls.extract_topics(combined)
        decisions = cls.extract_sentences(combined, DECISION_PATTERNS, limit=3)
        open_loops = cls.extract_sentences(combined, OPEN_LOOP_PATTERNS, limit=4)
        summary_parts = []
        if topics:
            summary_parts.append("Topics: " + ", ".join(topics[:5]))
        if decisions:
            summary_parts.append("Decisions: " + " ".join(decisions[:2]))
        if open_loops:
            summary_parts.append("Open loops: " + " ".join(open_loops[:3]))
        return ConversationContinuityState(
            topics=topics,
            decisions=decisions,
            open_loops=open_loops,
            summary=truncate(" ".join(summary_parts), 700),
        )

    @staticmethod
    def extract_topics(text: str, *, limit: int = 6) -> list[str]:
        tokens = [token for token in tokenize(text) if len(token) > 4 and token not in TOPIC_STOPWORDS]
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        ranked = sorted(counts.items(), key=lambda item: (item[1], len(item[0])), reverse=True)
        return [token for token, _ in ranked[:limit]]

    @staticmethod
    def extract_sentences(text: str, patterns: tuple[str, ...], *, limit: int) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
        selected: list[str] = []
        for sentence in sentences:
            clean = " ".join(sentence.strip().split())
            if len(clean) < 18:
                continue
            if any(re.search(pattern, clean, flags=re.IGNORECASE) for pattern in patterns):
                selected.append(truncate(clean, 220))
            if len(selected) >= limit:
                break
        return selected

    @staticmethod
    def merge_summary(previous: str, state: ConversationContinuityState) -> str:
        parts = [part for part in [previous.strip(), state.summary] if part]
        if not parts:
            return ""
        return truncate(" ".join(parts), 1200)

    @staticmethod
    def active_intent(state: ConversationContinuityState) -> str:
        if state.open_loops:
            return truncate("; ".join(state.open_loops[:3]), 500)
        if state.topics:
            return truncate("Continue: " + ", ".join(state.topics[:5]), 500)
        return ""

    @staticmethod
    def _relevance(query_tokens: set[str], content: str) -> float:
        if not query_tokens:
            return 0.0
        content_tokens = {token for token in tokenize(content) if len(token) > 3}
        if not content_tokens:
            return 0.0
        overlap = len(query_tokens & content_tokens)
        return overlap / len(query_tokens)
