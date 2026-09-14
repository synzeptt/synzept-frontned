"""User-approved understanding pipeline for long-term memory."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.memory.extraction_service import ConversationTurn, ExtractedMemory, MemoryExtractionService, MEMORY_TYPES
from app.memory.memory_service import MemoryService
from app.models.memory import Memory
from app.services.memory_trust_service import MemoryTrustService


UNDERSTANDING_CATEGORIES = frozenset(
    {
        "goals",
        "projects",
        "current_focus",
        "preferences",
        "habits",
        "relationships",
        "companies",
        "skills",
        "communication_style",
        "decision_style",
        "important_dates",
        "work_patterns",
        "learning_style",
        "other",
    }
)

SINGLETON_CATEGORIES = frozenset({"current_focus", "communication_style", "decision_style", "learning_style"})


@dataclass(slots=True)
class UnderstandingCandidate:
    item: ExtractedMemory
    category: str
    importance_level: str
    confidence: float
    reason: str
    observation_hash: str
    contradiction_id: UUID | None = None


@dataclass(slots=True)
class UnderstandingPipelineResult:
    extracted: list[UnderstandingCandidate] = field(default_factory=list)
    candidates_created: list[Memory] = field(default_factory=list)
    active_updated: list[Memory] = field(default_factory=list)
    duplicates_skipped: int = 0
    low_importance_skipped: int = 0

    @property
    def memory_count(self) -> int:
        return len(self.candidates_created) + len(self.active_updated)


class UnderstandingPipelineService:
    """Turns conversation signals into explainable, user-approved beliefs."""

    def __init__(self, session: AsyncSession, *, extractor: MemoryExtractionService | None = None) -> None:
        self.session = session
        self.extractor = extractor or MemoryExtractionService()
        self.memory_service = MemoryService(session, extractor=self.extractor)
        self.trust = MemoryTrustService(session)

    async def review_conversation(
        self,
        *,
        user_id: UUID,
        turns: list[ConversationTurn],
        conversation_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> UnderstandingPipelineResult:
        extracted = await self.extractor.extract_from_conversation(
            turns,
            conversation_id=conversation_id,
            project_id=project_id,
        )
        result = UnderstandingPipelineResult()
        for item in extracted:
            candidate = await self._candidate_for(item, user_id=user_id, conversation_id=conversation_id)
            if candidate is None:
                result.low_importance_skipped += 1
                continue
            result.extracted.append(candidate)
            if await self._already_processed(user_id, candidate.observation_hash):
                result.duplicates_skipped += 1
                continue
            existing = await self._matching_active(user_id, candidate)
            if existing:
                result.active_updated.append(await self._confirm_existing(existing, candidate))
                continue
            result.candidates_created.append(await self._create_pending_candidate(user_id, candidate))
        return result

    async def pending_candidates(self, user_id: UUID, *, limit: int = 50) -> list[Memory]:
        rows = list(
            (
                await self.session.execute(
                    select(Memory)
                    .where(Memory.user_id == user_id, Memory.deleted_at.is_(None), Memory.archived_at.is_not(None))
                    .order_by(Memory.importance_score.desc(), Memory.updated_at.desc())
                    .limit(limit)
                )
            ).scalars()
        )
        return [memory for memory in rows if self._status(memory) == "candidate"]

    async def approve_candidate(self, user_id: UUID, memory_id: UUID) -> Memory:
        memory = await self._owned(user_id, memory_id, include_archived=True)
        if self._status(memory) != "candidate":
            raise NotFoundError("Learning candidate not found")

        metadata = dict(memory.metadata_ or {})
        contradiction_id = self._uuid_or_none(metadata.get("contradicts_memory_id"))
        before = self.trust._snapshot(memory)
        duplicate = await self._matching_active(
            user_id,
            UnderstandingCandidate(
                item=ExtractedMemory(
                    memory_type=memory.memory_type,
                    content=memory.content,
                    summary=memory.summary or memory.content,
                    importance_score=memory.importance_score,
                    metadata=metadata,
                    conversation_id=memory.conversation_id,
                    project_id=memory.project_id,
                ),
                category=memory.category or memory.memory_type,
                importance_level=str(metadata.get("importance_level") or self._importance_level(memory.importance_score)),
                confidence=memory.confidence,
                reason=str(metadata.get("reason") or "User approved this learning."),
                observation_hash=str(metadata.get("observation_hash") or ""),
            ),
        )
        if duplicate and duplicate.id != memory.id:
            await self._merge_into_active(duplicate, memory)
            return duplicate

        if contradiction_id:
            old = await self._owned(user_id, contradiction_id, include_archived=True)
            old_before = self.trust._snapshot(old)
            old_metadata = dict(old.metadata_ or {})
            old_metadata["understanding_status"] = "archived"
            old_metadata["archived_reason"] = f"Superseded by approved memory {memory.id}."
            old.metadata_ = old_metadata
            old.archived_at = datetime.now(timezone.utc)
            old.version += 1
            await self.trust.record_event(
                user_id=user_id,
                memory_id=old.id,
                action="superseded",
                reason="User approved a newer belief that contradicted this one.",
                caused_by_type="user",
                caused_by_id=memory.id,
                before=old_before,
                after={"archived_at": old.archived_at.isoformat(), "status": "archived"},
            )

        metadata["understanding_status"] = "active"
        metadata["needs_approval"] = False
        metadata["approved_at"] = datetime.now(timezone.utc).isoformat()
        metadata["confirmations"] = int(metadata.get("confirmations", 0)) + 1
        memory.metadata_ = metadata
        memory.source = "user_approved_conversation"
        memory.archived_at = None
        memory.version += 1
        await self.session.flush()
        await self.memory_service._record_revision(memory, action="approved")
        await self.trust.record_event(
            user_id=user_id,
            memory_id=memory.id,
            action="approved",
            reason="User approved this learning for long-term understanding.",
            caused_by_type="user",
            before=before,
            after=self.trust._snapshot(memory) | {"status": "active"},
            metadata=metadata,
        )
        return memory

    async def reject_candidate(self, user_id: UUID, memory_id: UUID, *, reason: str | None = None) -> None:
        memory = await self._owned(user_id, memory_id, include_archived=True)
        if self._status(memory) != "candidate":
            raise NotFoundError("Learning candidate not found")
        before = self.trust._snapshot(memory)
        metadata = dict(memory.metadata_ or {})
        metadata["understanding_status"] = "rejected"
        metadata["rejected_at"] = datetime.now(timezone.utc).isoformat()
        metadata["rejections"] = int(metadata.get("rejections", 0)) + 1
        memory.metadata_ = metadata
        memory.deleted_at = datetime.now(timezone.utc)
        memory.version += 1
        await self.session.flush()
        await self.memory_service._record_revision(memory, action="rejected")
        await self.trust.record_event(
            user_id=user_id,
            memory_id=memory.id,
            action="rejected",
            reason=reason or "User chose not to remember this learning.",
            caused_by_type="user",
            before=before,
            after={"deleted_at": memory.deleted_at.isoformat(), "status": "rejected"},
            metadata=metadata,
        )

    async def lifecycle(self, user_id: UUID, memory_id: UUID, status: str, *, reason: str | None = None) -> Memory:
        if status not in {"inactive", "archived", "forgotten"}:
            raise ValueError("Unsupported understanding lifecycle status")
        memory = await self._owned(user_id, memory_id, include_archived=True)
        before = self.trust._snapshot(memory)
        metadata = dict(memory.metadata_ or {})
        metadata["understanding_status"] = status
        metadata[f"{status}_at"] = datetime.now(timezone.utc).isoformat()
        if reason:
            metadata[f"{status}_reason"] = reason
        memory.metadata_ = metadata
        memory.archived_at = datetime.now(timezone.utc)
        if status == "forgotten":
            memory.deleted_at = datetime.now(timezone.utc)
        memory.version += 1
        await self.session.flush()
        await self.memory_service._record_revision(memory, action=status)
        await self.trust.record_event(
            user_id=user_id,
            memory_id=memory.id,
            action=status,
            reason=reason or f"User marked this understanding as {status}.",
            caused_by_type="user",
            before=before,
            after=self.trust._snapshot(memory) | {"status": status},
            metadata=metadata,
        )
        return memory

    async def relevant_understanding(
        self,
        user_id: UUID,
        *,
        query: str | None = None,
        category: str | None = None,
        limit: int = 8,
    ) -> list[Memory]:
        statement = select(Memory).where(Memory.user_id == user_id, Memory.deleted_at.is_(None), Memory.archived_at.is_(None))
        if category:
            statement = statement.where(Memory.category == self._normalize_category(category))
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(or_(Memory.content.ilike(pattern), Memory.summary.ilike(pattern)))
        memories = list(
            (
                await self.session.execute(
                    statement.order_by(Memory.pinned.desc(), Memory.importance_score.desc(), Memory.confidence.desc(), Memory.updated_at.desc()).limit(limit)
                )
            ).scalars()
        )
        usable = [memory for memory in memories if self._status(memory) in {"active", "manual", ""}]
        await self.memory_service.mark_retrieved(usable)
        return usable

    async def _candidate_for(self, item: ExtractedMemory, *, user_id: UUID, conversation_id: UUID | None) -> UnderstandingCandidate | None:
        category = self._normalize_category(item.memory_type)
        confidence = min(max(item.importance_score, 0.0), 1.0)
        importance_level = self._importance_level(confidence)
        if importance_level == "low":
            return None
        observation_hash = self._observation_hash(user_id, conversation_id, category, item.content)
        contradiction_id = await self._contradiction(user_id, category, item.content)
        reason = self._reason(category, importance_level, bool(contradiction_id))
        return UnderstandingCandidate(
            item=item,
            category=category,
            importance_level=importance_level,
            confidence=confidence,
            reason=reason,
            observation_hash=observation_hash,
            contradiction_id=contradiction_id,
        )

    async def _create_pending_candidate(self, user_id: UUID, candidate: UnderstandingCandidate) -> Memory:
        now = datetime.now(timezone.utc)
        metadata = {
            **dict(candidate.item.metadata or {}),
            "understanding_status": "candidate",
            "importance_level": candidate.importance_level,
            "reason": candidate.reason,
            "needs_approval": True,
            "confidence_percent": round(candidate.confidence * 100),
            "source_conversation_id": str(candidate.item.conversation_id) if candidate.item.conversation_id else None,
            "last_confirmed_at": None,
            "confirmations": 0,
            "observation_hash": candidate.observation_hash,
            "pipeline": "understanding_v1",
        }
        if candidate.contradiction_id:
            metadata["contradiction"] = True
            metadata["contradicts_memory_id"] = str(candidate.contradiction_id)
            metadata["contradiction_prompt"] = "This may replace something Synzept already believes. Please choose which is true."
        memory_type = candidate.category if candidate.category in MEMORY_TYPES else "other"
        memory = Memory(
            user_id=user_id,
            conversation_id=candidate.item.conversation_id,
            project_id=candidate.item.project_id,
            memory_type=memory_type,
            category=candidate.category,
            content=candidate.item.content,
            summary=candidate.item.summary,
            source="conversation_candidate",
            confidence=candidate.confidence,
            importance_score=candidate.confidence,
            recency_score=1.0,
            retrieval_count=0,
            version=1,
            archived_at=now,
            metadata_=metadata,
            content_hash=MemoryService._content_hash(candidate.item.content),
        )
        self.session.add(memory)
        await self.session.flush()
        await self.memory_service._record_revision(memory, action="candidate")
        await self.trust.record_event(
            user_id=user_id,
            memory_id=memory.id,
            action="candidate_created",
            reason="I think this is worth remembering. It needs your approval before Synzept uses it.",
            caused_by_type="conversation",
            caused_by_id=candidate.item.conversation_id,
            after=self.trust._snapshot(memory) | {"status": "candidate"},
            metadata=metadata,
        )
        return memory

    async def _confirm_existing(self, memory: Memory, candidate: UnderstandingCandidate) -> Memory:
        metadata = dict(memory.metadata_ or {})
        metadata["confirmations"] = int(metadata.get("confirmations", 0)) + 1
        metadata["last_confirmed_at"] = datetime.now(timezone.utc).isoformat()
        metadata["last_observation_hash"] = candidate.observation_hash
        metadata["importance_level"] = self._importance_level(max(memory.importance_score, candidate.confidence))
        memory.metadata_ = metadata
        memory.confidence = max(memory.confidence, candidate.confidence)
        memory.importance_score = max(memory.importance_score, candidate.confidence)
        memory.conversation_id = candidate.item.conversation_id or memory.conversation_id
        memory.project_id = candidate.item.project_id or memory.project_id
        memory.version += 1
        await self.session.flush()
        await self.memory_service._record_revision(memory, action="confirmed")
        await self.trust.record_event(
            user_id=memory.user_id,
            memory_id=memory.id,
            action="confirmed",
            reason="A new conversation confirmed this approved understanding.",
            caused_by_type="conversation",
            caused_by_id=candidate.item.conversation_id,
            after=self.trust._snapshot(memory),
            metadata=metadata,
        )
        return memory

    async def _merge_into_active(self, active: Memory, candidate: Memory) -> None:
        before = self.trust._snapshot(active)
        metadata = dict(active.metadata_ or {})
        candidate_metadata = dict(candidate.metadata_ or {})
        metadata["confirmations"] = int(metadata.get("confirmations", 0)) + int(candidate_metadata.get("confirmations", 0)) + 1
        metadata["last_confirmed_at"] = datetime.now(timezone.utc).isoformat()
        active.metadata_ = metadata
        active.confidence = max(active.confidence, candidate.confidence)
        active.importance_score = max(active.importance_score, candidate.importance_score)
        active.version += 1
        candidate.deleted_at = datetime.now(timezone.utc)
        candidate_metadata["understanding_status"] = "merged"
        candidate.metadata_ = candidate_metadata
        await self.session.flush()
        await self.memory_service._record_revision(active, action="merged")
        await self.trust.record_event(
            user_id=active.user_id,
            memory_id=active.id,
            action="merged",
            reason="Approved candidate matched an existing belief, so Synzept strengthened the existing belief.",
            caused_by_type="user",
            caused_by_id=candidate.id,
            before=before,
            after=self.trust._snapshot(active),
            metadata={"merged_candidate_id": str(candidate.id), **metadata},
        )

    async def _already_processed(self, user_id: UUID, observation_hash: str) -> bool:
        rows = list(
            (
                await self.session.execute(
                    select(Memory).where(Memory.user_id == user_id).order_by(Memory.updated_at.desc()).limit(500)
                )
            ).scalars()
        )
        return any((memory.metadata_ or {}).get("observation_hash") == observation_hash or (memory.metadata_ or {}).get("last_observation_hash") == observation_hash for memory in rows)

    async def _matching_active(self, user_id: UUID, candidate: UnderstandingCandidate) -> Memory | None:
        result = await self.session.execute(
            select(Memory).where(
                Memory.user_id == user_id,
                Memory.category == candidate.category,
                Memory.content_hash == MemoryService._content_hash(candidate.item.content),
                Memory.deleted_at.is_(None),
                Memory.archived_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def _contradiction(self, user_id: UUID, category: str, content: str) -> UUID | None:
        if category not in SINGLETON_CATEGORIES:
            return None
        rows = list(
            (
                await self.session.execute(
                    select(Memory)
                    .where(Memory.user_id == user_id, Memory.category == category, Memory.deleted_at.is_(None), Memory.archived_at.is_(None))
                    .order_by(Memory.updated_at.desc())
                    .limit(5)
                )
            ).scalars()
        )
        normalized = self._semantic_key(content)
        for memory in rows:
            if self._semantic_key(memory.content) != normalized:
                return memory.id
        return None

    async def _owned(self, user_id: UUID, memory_id: UUID, *, include_archived: bool = False) -> Memory:
        statement = select(Memory).where(Memory.user_id == user_id, Memory.id == memory_id, Memory.deleted_at.is_(None))
        if not include_archived:
            statement = statement.where(Memory.archived_at.is_(None))
        memory = (await self.session.execute(statement)).scalar_one_or_none()
        if not memory:
            raise NotFoundError("Memory not found")
        return memory

    @staticmethod
    def _normalize_category(value: str | None) -> str:
        normalized = (value or "other").lower().replace("-", "_").replace(" ", "_")
        mapping = {
            "priorities": "current_focus",
            "routines": "habits",
            "routine": "habits",
            "work": "work_patterns",
            "decisions": "decision_style",
            "identity": "other",
            "interests": "learning_style",
            "long_term_plans": "goals",
        }
        normalized = mapping.get(normalized, normalized)
        return normalized if normalized in UNDERSTANDING_CATEGORIES else "other"

    @staticmethod
    def _importance_level(score: float) -> str:
        if score >= 0.9:
            return "critical"
        if score >= 0.75:
            return "high"
        if score >= 0.5:
            return "medium"
        return "low"

    @staticmethod
    def _reason(category: str, importance_level: str, contradiction: bool) -> str:
        if contradiction:
            return "This appears to change an existing belief, so Synzept needs you to choose what is true."
        return f"This {importance_level} {category.replace('_', ' ')} signal may help Synzept personalize future conversations."

    @staticmethod
    def _status(memory: Memory) -> str:
        metadata = memory.metadata_ or {}
        if memory.deleted_at:
            return str(metadata.get("understanding_status") or "forgotten")
        if memory.archived_at:
            return str(metadata.get("understanding_status") or "archived")
        return str(metadata.get("understanding_status") or "active")

    @staticmethod
    def _semantic_key(value: str) -> str:
        return re.sub(r"\W+", " ", value.casefold()).strip()

    @staticmethod
    def _observation_hash(user_id: UUID, conversation_id: UUID | None, category: str, content: str) -> str:
        payload = f"{user_id}:{conversation_id}:{category}:{UnderstandingPipelineService._semantic_key(content)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _uuid_or_none(value: object) -> UUID | None:
        try:
            return UUID(str(value)) if value else None
        except (TypeError, ValueError):
            return None
