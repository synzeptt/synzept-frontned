from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.memory.memory_service import MemoryService
from app.models.goal import Goal
from app.models.memory import Memory, MemoryRevision, MemoryTrustEvent
from app.models.message import Message
from app.models.project import Project
from app.models.project_intelligence_phase2 import Decision, OpenLoop
from app.schemas.memory import (
    ConnectedEntityOut,
    MemoryExplainOut,
    MemoryExplorerItemOut,
    MemoryOut,
    MemoryTrustEventOut,
)


class MemoryTrustService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def explorer(self, user_id: UUID, *, include_ignored: bool = False) -> list[MemoryExplorerItemOut]:
        statement = select(Memory).where(Memory.user_id == user_id)
        if not include_ignored:
            statement = statement.where(Memory.deleted_at.is_(None))
        result = await self.session.execute(statement.order_by(Memory.updated_at.desc()).limit(200))
        return [await self._explorer_item(memory) for memory in result.scalars()]

    async def timeline(self, user_id: UUID, memory_id: UUID) -> list[MemoryTrustEventOut]:
        memory = await self._owned_memory(user_id, memory_id, include_deleted=True)
        events = await self._events(memory.id)
        if events:
            return [self._event_out(event) for event in events]
        revisions = list(
            (
                await self.session.execute(
                    select(MemoryRevision).where(MemoryRevision.memory_id == memory.id).order_by(MemoryRevision.created_at.desc())
                )
            ).scalars()
        )
        return [
            MemoryTrustEventOut(
                id=revision.id,
                memory_id=memory.id,
                action=revision.action,
                reason=f"Memory was {revision.action}.",
                caused_by_type="revision",
                caused_by_id=revision.id,
                before={},
                after={"content": revision.content, "category": revision.category, "importance": revision.importance_score},
                metadata={},
                created_at=revision.created_at,
            )
            for revision in revisions
        ]

    async def update_memory(
        self,
        user_id: UUID,
        memory_id: UUID,
        *,
        content: str | None,
        category: str | None,
        importance: float | None,
        reason: str | None,
    ) -> Memory:
        memory = await self._owned_memory(user_id, memory_id)
        before = self._snapshot(memory)
        updated = await MemoryService(self.session).update_memory(
            user_id=user_id,
            memory_id=memory_id,
            content=content,
            category=category,
            importance_score=importance,
        )
        await self.record_event(
            user_id=user_id,
            memory_id=memory_id,
            action="edited",
            reason=reason or "User edited this memory.",
            caused_by_type="user",
            before=before,
            after=self._snapshot(updated),
        )
        return updated

    async def merge(self, user_id: UUID, target_memory_id: UUID, source_memory_id: UUID, *, reason: str | None = None) -> Memory:
        target = await self._owned_memory(user_id, target_memory_id)
        source = await self._owned_memory(user_id, source_memory_id)
        before = self._snapshot(target)
        if source.content not in target.content:
            target.content = f"{target.content}\n\n{source.content}"
        target.summary = target.summary or source.summary
        target.importance_score = max(target.importance_score, source.importance_score)
        target.confidence = max(target.confidence, source.confidence)
        target.version += 1
        source.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        await MemoryService(self.session)._record_revision(target, action="merged")
        await self.record_event(
            user_id=user_id,
            memory_id=target.id,
            action="merged",
            reason=reason or "User merged another memory into this one.",
            caused_by_type="user",
            caused_by_id=source.id,
            before=before,
            after=self._snapshot(target),
            metadata={"merged_memory_id": str(source.id)},
        )
        await self.record_event(
            user_id=user_id,
            memory_id=source.id,
            action="merged_into",
            reason=f"Merged into memory {target.id}.",
            caused_by_type="user",
            caused_by_id=target.id,
            before=self._snapshot(source),
            after={"deleted_at": source.deleted_at.isoformat()},
        )
        return target

    async def ignore(self, user_id: UUID, memory_id: UUID, *, reason: str | None = None) -> None:
        memory = await self._owned_memory(user_id, memory_id)
        before = self._snapshot(memory)
        memory.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.record_event(
            user_id=user_id,
            memory_id=memory_id,
            action="ignored",
            reason=reason or "User ignored this memory. Synzept will no longer use it.",
            caused_by_type="user",
            before=before,
            after={"deleted_at": memory.deleted_at.isoformat()},
        )

    async def delete(self, user_id: UUID, memory_id: UUID, *, reason: str | None = None) -> None:
        memory = await self._owned_memory(user_id, memory_id)
        before = self._snapshot(memory)
        await MemoryService(self.session).delete_memory(user_id=user_id, memory_id=memory_id)
        await self.record_event(
            user_id=user_id,
            memory_id=memory_id,
            action="deleted",
            reason=reason or "User deleted this memory.",
            caused_by_type="user",
            before=before,
            after={"deleted_at": datetime.now(timezone.utc).isoformat()},
        )

    async def explain_message(self, user_id: UUID, message_id: UUID) -> MemoryExplainOut:
        result = await self.session.execute(select(Message).where(Message.id == message_id).limit(1))
        message = result.scalar_one_or_none()
        if not message:
            raise NotFoundError("Message not found")
        metadata = message.metadata_ or {}
        trust = metadata.get("trust_context") or {}
        memory_ids = [UUID(item["id"]) for item in trust.get("memories", []) if item.get("id")]
        memories = []
        if memory_ids:
            memories = list((await self.session.execute(select(Memory).where(Memory.user_id == user_id, Memory.id.in_(memory_ids)))).scalars())
        projects = await self._entities(Project, user_id, trust.get("projects", []), "project")
        loops = await self._entities(OpenLoop, user_id, trust.get("open_loops", []), "open_loop")
        decisions = await self._entities(Decision, user_id, trust.get("decisions", []), "decision")
        return MemoryExplainOut(
            message_id=message_id,
            memories_used=memories,
            projects_used=projects,
            open_loops_used=loops,
            decisions_used=decisions,
            explanation="Synzept used the visible context listed here to continue the conversation. You can edit, ignore, or delete any memory.",
        )

    async def record_event(
        self,
        *,
        user_id: UUID,
        memory_id: UUID | None,
        action: str,
        reason: str,
        caused_by_type: str,
        caused_by_id: UUID | None = None,
        before: dict | None = None,
        after: dict | None = None,
        metadata: dict | None = None,
    ) -> None:
        self.session.add(
            MemoryTrustEvent(
                user_id=user_id,
                memory_id=memory_id,
                action=action,
                reason=reason,
                caused_by_type=caused_by_type,
                caused_by_id=caused_by_id,
                before=before or {},
                after=after or {},
                metadata_=metadata or {},
            )
        )
        await self.session.flush()

    async def _explorer_item(self, memory: Memory) -> MemoryExplorerItemOut:
        return MemoryExplorerItemOut(
            memory=memory,
            connected_projects=await self._connected_projects(memory),
            connected_goals=await self._connected_goals(memory),
            timeline=[self._event_out(event) for event in (await self._events(memory.id))[:4]],
        )

    async def _owned_memory(self, user_id: UUID, memory_id: UUID, *, include_deleted: bool = False) -> Memory:
        statement = select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
        if not include_deleted:
            statement = statement.where(Memory.deleted_at.is_(None))
        memory = (await self.session.execute(statement)).scalar_one_or_none()
        if not memory:
            raise NotFoundError("Memory not found")
        return memory

    async def _events(self, memory_id: UUID) -> list[MemoryTrustEvent]:
        return list(
            (
                await self.session.execute(
                    select(MemoryTrustEvent).where(MemoryTrustEvent.memory_id == memory_id).order_by(MemoryTrustEvent.created_at.desc()).limit(40)
                )
            ).scalars()
        )

    async def _connected_projects(self, memory: Memory) -> list[ConnectedEntityOut]:
        if not memory.project_id:
            return []
        project = await self.session.get(Project, memory.project_id)
        if not project:
            return []
        return [ConnectedEntityOut(id=project.id, title=project.name, type="project")]

    async def _connected_goals(self, memory: Memory) -> list[ConnectedEntityOut]:
        if not memory.project_id:
            return []
        goals = list((await self.session.execute(select(Goal).where(Goal.project_id == memory.project_id, Goal.deleted_at.is_(None)).limit(5))).scalars())
        return [ConnectedEntityOut(id=goal.id, title=goal.title, type="goal") for goal in goals]

    async def _entities(self, model, user_id: UUID, ids: list[str], entity_type: str) -> list[ConnectedEntityOut]:
        if not ids:
            return []
        uuids = [UUID(value) for value in ids]
        if model is OpenLoop or model is Decision:
            rows = list((await self.session.execute(select(model).join(Project, model.project_id == Project.id).where(Project.user_id == user_id, model.id.in_(uuids)))).scalars())
        else:
            rows = list((await self.session.execute(select(model).where(model.user_id == user_id, model.id.in_(uuids)))).scalars())
        return [ConnectedEntityOut(id=row.id, title=getattr(row, "name", None) or row.title, type=entity_type) for row in rows]

    @staticmethod
    def _snapshot(memory: Memory) -> dict:
        return {
            "content": memory.content,
            "category": memory.category,
            "memory_type": memory.memory_type,
            "importance": memory.importance_score,
            "confidence": memory.confidence,
            "source": memory.source,
            "version": memory.version,
        }

    @staticmethod
    def _event_out(event: MemoryTrustEvent) -> MemoryTrustEventOut:
        return MemoryTrustEventOut(
            id=event.id,
            memory_id=event.memory_id,
            action=event.action,
            reason=event.reason,
            caused_by_type=event.caused_by_type,
            caused_by_id=event.caused_by_id,
            before=event.before or {},
            after=event.after or {},
            metadata=event.metadata_ or {},
            created_at=event.created_at,
        )
