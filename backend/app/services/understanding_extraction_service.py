from __future__ import annotations

import re
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.extraction_service import ConversationTurn, MemoryExtractionService
from app.models.conversation import Conversation
from app.models.memory import Memory
from app.models.message import Message


@dataclass(slots=True)
class UnderstandingFact:
    category: str
    section: str
    field: str
    title: str
    value: str
    confidence: float = 0.65
    source: str = "learned"
    evidence: list[str] = field(default_factory=list)


class UnderstandingExtractionService:
    """Extracts structured user-understanding facts from memories and recent turns."""

    def __init__(self, session: AsyncSession, *, memory_extractor: MemoryExtractionService | None = None) -> None:
        self.session = session
        self.memory_extractor = memory_extractor or MemoryExtractionService()

    async def extract_for_user(self, user_id: UUID, *, memory_limit: int = 200, message_limit: int = 80) -> list[UnderstandingFact]:
        memories = await self._recent_memories(user_id, memory_limit)
        facts = [fact for memory in memories for fact in self.extract_from_memory(memory)]
        facts.extend(await self._extract_from_recent_messages(user_id, message_limit))
        return self._dedupe(facts)

    def extract_from_memory(self, memory: Memory) -> list[UnderstandingFact]:
        text = (memory.summary or memory.content or "").strip()
        if not text:
            return []
        memory_type = (memory.memory_type or memory.category or "work").lower()
        confidence = max(min(memory.confidence or memory.importance_score or 0.65, 1.0), 0.0)
        evidence = [text[:260]]

        if person := self._important_person(text):
            return [self._fact("important_people", "relationships", "importantPeople", "Important people", person, confidence, evidence)]
        if self._looks_like_health_goal(text):
            return [self._fact("health_goals", "personal_life", "healthGoals", "Health goals", text, confidence, evidence)]

        if memory_type == "identity":
            field = "name" if re.search(r"\bmy name is\b", text, re.I) else "background"
            return [self._fact("about_me", "identity", field, "Identity", self._clean_identity(text), confidence, evidence)]
        if memory_type == "interests":
            return [self._fact("interests", "personal_life", "interests", "Interests", text, confidence, evidence)]
        if memory_type == "routines":
            return [self._fact("habits", "personal_life", "habits", "Habits", text, confidence, evidence)]
        if memory_type == "preferences":
            return [self._fact("preferences", "personal_life", "preferences", "Preferences", text, confidence, evidence)]
        if memory_type == "work":
            return [self._fact(self._work_category(text), "professional_life", self._work_field(text), "Professional life", text, confidence, evidence)]
        if memory_type == "projects":
            category = "startup" if "startup" in text.casefold() else "projects"
            return [self._fact(category, "professional_life", "projects", "Projects", text, confidence, evidence)]
        if memory_type == "goals":
            category, field, title = self._goal_bucket(text)
            return [self._fact(category, "goals", field, title, text, confidence, evidence)]
        if memory_type == "long_term_plans":
            return [self._fact("long_term_goals", "goals", "longTermGoals", "Long-term goals", text, confidence, evidence)]
        if memory_type == "decisions":
            return [self._fact("commitments", "relationships", "commitments", "Commitments", text, confidence, evidence)]
        if memory_type == "priorities":
            return [
                self._fact("current_focus", "current_state", "currentFocus", "Current focus", text, confidence, evidence),
                self._fact("priorities", "intelligence", "priorities", "Priorities", text, confidence, evidence),
            ]
        if memory_type == "skills":
            return [self._fact("skills", "professional_life", "responsibilities", "Skills and responsibilities", text, confidence, evidence)]
        return [self._fact("about_me", "identity", "personalInformation", "Personal information", text, confidence, evidence)]

    async def _extract_from_recent_messages(self, user_id: UUID, limit: int) -> list[UnderstandingFact]:
        result = await self.session.execute(
            select(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None), Message.role == "user")
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        turns = [ConversationTurn(role="user", content=message.content) for message in result.scalars()]
        extracted = await self.memory_extractor.extract_from_conversation(turns)
        pseudo_memories = [
            Memory(memory_type=item.memory_type, content=item.content, summary=item.summary, confidence=item.importance_score, importance_score=item.importance_score)
            for item in extracted
        ]
        facts = [fact for memory in pseudo_memories for fact in self.extract_from_memory(memory)]
        for turn in turns:
            facts.extend(self._explicit_recent_message_facts(turn.content))
        return self._dedupe(facts)

    async def _recent_memories(self, user_id: UUID, limit: int) -> list[Memory]:
        result = await self.session.execute(
            select(Memory)
            .where(Memory.user_id == user_id, Memory.deleted_at.is_(None))
            .order_by(Memory.importance_score.desc(), Memory.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars())

    @staticmethod
    def _fact(category: str, section: str, field: str, title: str, value: str, confidence: float, evidence: list[str]) -> UnderstandingFact:
        return UnderstandingFact(category=category, section=section, field=field, title=title, value=value.strip(), confidence=confidence, evidence=evidence)

    def _explicit_recent_message_facts(self, text: str) -> list[UnderstandingFact]:
        cleaned = " ".join((text or "").strip().split())
        if not cleaned:
            return []
        facts: list[UnderstandingFact] = []
        if re.search(r"\b(my goal is|i want to|i need to|i'm trying to|i am trying to)\b", cleaned, flags=re.I):
            facts.append(self._fact("short_term_goals", "goals", "shortTermGoals", "Short-term goals", cleaned, 0.8, [cleaned[:260]]))
        if re.search(r"\b(i prefer|i like|i dislike|my preference is|i want you to)\b", cleaned, flags=re.I):
            facts.append(self._fact("preferences", "personal_life", "preferences", "Preferences", cleaned, 0.72, [cleaned[:260]]))
        if re.search(r"\b(blocker|blocked|struggle|stuck|urgent)\b", cleaned, flags=re.I):
            facts.append(self._fact("current_struggles", "current_state", "currentStruggles", "Current struggles", cleaned, 0.76, [cleaned[:260]]))
        return facts

    @staticmethod
    def _goal_bucket(text: str) -> tuple[str, str, str]:
        lowered = text.casefold()
        if "mission" in lowered or "north star" in lowered:
            return "missions", "mission", "Mission"
        if "long-term" in lowered or "long term" in lowered or "eventually" in lowered or "next year" in lowered:
            return "long_term_goals", "longTermGoals", "Long-term goals"
        return "short_term_goals", "shortTermGoals", "Short-term goals"

    @staticmethod
    def _work_category(text: str) -> str:
        lowered = text.casefold()
        if "company" in lowered or "startup" in lowered or "client" in lowered:
            return "company"
        if "role" in lowered or "job" in lowered or "work as" in lowered:
            return "job"
        return "responsibilities"

    @staticmethod
    def _work_field(text: str) -> str:
        category = UnderstandingExtractionService._work_category(text)
        return {"company": "company", "job": "role"}.get(category, "responsibilities")

    @staticmethod
    def _important_person(text: str) -> str:
        match = re.search(r"\bmy\s+(cofounder|co-founder|partner|wife|husband|friend|manager|mentor|client)\s+([A-Z][A-Za-z]+)\b", text)
        return f"{match.group(1)} {match.group(2)}" if match else ""

    @staticmethod
    def _looks_like_health_goal(text: str) -> bool:
        return bool(re.search(r"\b(health|fitness|sleep|workout|exercise|diet|meditation|therapy)\b", text, re.I))

    @staticmethod
    def _clean_identity(text: str) -> str:
        match = re.search(r"\bmy name is\s+([^,.!?;]+)", text, re.I)
        return match.group(1).strip() if match else text

    @staticmethod
    def _dedupe(facts: list[UnderstandingFact]) -> list[UnderstandingFact]:
        seen: set[tuple[str, str]] = set()
        output: list[UnderstandingFact] = []
        for fact in facts:
            key = (fact.category, " ".join(fact.value.casefold().split()))
            if not fact.value or key in seen:
                continue
            seen.add(key)
            output.append(fact)
        return output
