"""Structured memory intelligence for conversation-driven knowledge capture."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.extraction_service import ConversationTurn, ExtractedMemory, MemoryExtractionService
from app.memory.memory_service import MemoryService
from app.models.user import User
from app.schemas.core import TimelineEventCreate
from app.services.relationship_graph_phase5_service import RelationshipGraphPhase5Service
from app.services.timeline_service import TimelineService
from app.services.understanding_engine_service import UnderstandingEngineService
from app.services.understanding_extraction_service import UnderstandingFact
from app.services.understanding_update_service import UnderstandingUpdateService

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeFact:
    category: str
    section: str
    field: str
    title: str
    value: str
    confidence: float = 0.75
    source: str = "conversation"
    evidence: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryIntelligenceResult:
    user_id: UUID
    extracted_memories: list[ExtractedMemory] = field(default_factory=list)
    memory_count: int = 0
    structured_facts_created: int = 0
    structured_facts_updated: int = 0
    decision_facts: list[UnderstandingFact] = field(default_factory=list)
    open_loop_facts: list[UnderstandingFact] = field(default_factory=list)
    relationship_graph_refreshed: bool = False
    timeline_events_created: int = 0


class DecisionService:
    DECISION_PATTERNS = (
        r"\b(decided|decision|we chose|we picked|settled on|approved|we will|let's use|we should use|i will|i plan to)\b",
    )

    def extract(self, turns: list[ConversationTurn]) -> list[UnderstandingFact]:
        facts: list[UnderstandingFact] = []
        for turn in turns:
            if turn.role != "user":
                continue
            content = self._normalized_text(turn.content)
            if len(content) < 20:
                continue
            if any(re.search(pattern, content, flags=re.IGNORECASE) for pattern in self.DECISION_PATTERNS):
                facts.append(
                    UnderstandingFact(
                        category="commitments",
                        section="relationships",
                        field="commitments",
                        title="Decision",
                        value=content,
                        confidence=0.8,
                        source="conversation",
                        evidence=[content],
                    )
                )
        return self._dedupe(facts)

    @staticmethod
    def _normalized_text(text: str) -> str:
        return " ".join(text.strip().split())

    @staticmethod
    def _dedupe(facts: list[UnderstandingFact]) -> list[UnderstandingFact]:
        seen: set[str] = set()
        unique: list[UnderstandingFact] = []
        for fact in facts:
            key = fact.value.casefold().strip()
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(fact)
        return unique


class OpenLoopService:
    OPEN_LOOP_PATTERNS = (
        r"\b(need to|need help|follow up|waiting on|waiting for|blocker|blocked|stuck|next step|todo:|to do|should do)\b",
    )

    def extract(self, turns: list[ConversationTurn]) -> list[UnderstandingFact]:
        facts: list[UnderstandingFact] = []
        for turn in turns:
            if turn.role != "user":
                continue
            content = self._normalized_text(turn.content)
            if len(content) < 20:
                continue
            if any(re.search(pattern, content, flags=re.IGNORECASE) for pattern in self.OPEN_LOOP_PATTERNS):
                facts.append(
                    UnderstandingFact(
                        category="open_loops",
                        section="current_state",
                        field="openLoops",
                        title="Open loop",
                        value=content,
                        confidence=0.72,
                        source="conversation",
                        evidence=[content],
                    )
                )
        return self._dedupe(facts)

    @staticmethod
    def _normalized_text(text: str) -> str:
        return " ".join(text.strip().split())

    @staticmethod
    def _dedupe(facts: list[UnderstandingFact]) -> list[UnderstandingFact]:
        seen: set[str] = set()
        unique: list[UnderstandingFact] = []
        for fact in facts:
            key = fact.value.casefold().strip()
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(fact)
        return unique


class TimelineUpdateService:
    def __init__(self, session: AsyncSession) -> None:
        self._service = TimelineService(session)

    async def record_decision_events(self, user_id: UUID, facts: list[UnderstandingFact]) -> int:
        created = 0
        for fact in facts:
            if fact.category != "commitments":
                continue
            event = TimelineEventCreate(
                event_type="decision",
                title=fact.title,
                description=fact.value,
                importance=min(max(fact.confidence, 0.4), 0.95),
                event_date=date.today(),
            )
            await self._service.create(user_id, event)
            created += 1
        return created


class EntityLinkingService:
    def __init__(self, session: AsyncSession) -> None:
        self._service = RelationshipGraphPhase5Service(session)

    async def refresh(self, user_id: UUID) -> None:
        await self._service.refresh(user_id)


class MemoryIntelligenceEngine:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.memory_service = MemoryService(session)
        self.understanding_engine = UnderstandingEngineService(session)
        self.understanding_update = UnderstandingUpdateService(session)
        self.entity_linking = EntityLinkingService(session)
        self.timeline_update = TimelineUpdateService(session)
        self.decision_service = DecisionService()
        self.open_loop_service = OpenLoopService()
        self.extractor = MemoryExtractionService()

    async def process_conversation(
        self,
        *,
        user_id: UUID,
        turns: list[ConversationTurn],
        conversation_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> MemoryIntelligenceResult:
        extracted_memories = await self.extractor.extract_from_conversation(
            turns,
            conversation_id=conversation_id,
            project_id=project_id,
        )

        structured_facts = self._extract_structured_facts(turns)
        decision_facts = [fact for fact in structured_facts if fact.category == "commitments"]
        open_loop_facts = [fact for fact in structured_facts if fact.category == "open_loops"]

        stored_memories = await self.memory_service.process_conversation(
            user_id=user_id,
            turns=turns,
            conversation_id=conversation_id,
            project_id=project_id,
        )

        user = await self.session.get(User, user_id)
        created = 0
        updated = 0
        relationship_graph_refreshed = False
        timeline_events_created = 0

        if user and stored_memories:
            created_count, _ = await self.understanding_engine.refresh_from_memories(user, stored_memories)
            created += created_count

        if user and structured_facts:
            result = await self.understanding_update.apply_facts(user_id, structured_facts)
            created += result.created
            updated += result.updated

        if user and (stored_memories or structured_facts):
            await self.entity_linking.refresh(user_id)
            relationship_graph_refreshed = True

        if user and decision_facts:
            timeline_events_created = await self.timeline_update.record_decision_events(user_id, decision_facts)

        return MemoryIntelligenceResult(
            user_id=user_id,
            extracted_memories=extracted_memories,
            memory_count=len(stored_memories),
            structured_facts_created=created,
            structured_facts_updated=updated,
            decision_facts=decision_facts,
            open_loop_facts=open_loop_facts,
            relationship_graph_refreshed=relationship_graph_refreshed,
            timeline_events_created=timeline_events_created,
        )

    def _extract_structured_facts(self, turns: list[ConversationTurn]) -> list[UnderstandingFact]:
        decisions = self.decision_service.extract(turns)
        open_loops = self.open_loop_service.extract(turns)
        return [*decisions, *open_loops]
