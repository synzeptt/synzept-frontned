"""Project memory: persistent context for ongoing work."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.types import ProjectContext
from app.models.conversation import Conversation
from app.models.project_context import ProjectContext as ProjectContextEntry
from app.models.memory import Memory
from app.models.note import Note
from app.models.project import Project
from app.models.task import Task
from app.utils.text import truncate

logger = logging.getLogger(__name__)


class ProjectMemory:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load(self, user_id: UUID, project_id: UUID) -> ProjectContext | None:
        project = await self.session.get(Project, project_id)
        if not project or project.user_id != user_id or project.deleted_at:
            return None

        notes = await self._load_notes(project_id)
        tasks = await self._load_tasks(project_id)
        project_memories = await self._load_project_memories(user_id, project_id)
        decisions = [m for m in project_memories if "decision" in m.lower()][:5]

        context_entries = await self._load_context_entries(project_id)
        summary_parts = [project.context_summary or "", project.description or "", *context_entries]
        summary = "\n".join(p for p in summary_parts if p).strip()

        return ProjectContext(
            project_id=project.id,
            name=project.name,
            summary=truncate(summary, 800),
            notes=notes,
            tasks=tasks,
            decisions=decisions,
        )

    async def update_summary(self, user_id: UUID, project_id: UUID, new_insight: str) -> None:
        """Merge new insight into project context summary (lightweight update)."""
        project = await self.session.get(Project, project_id)
        if not project or project.user_id != user_id:
            return
        existing = project.context_summary or ""
        if new_insight.lower() in existing.lower():
            return
        combined = f"{existing}\n- {new_insight}".strip() if existing else new_insight
        project.context_summary = truncate(combined, 2000)

    async def _load_context_entries(self, project_id: UUID, limit: int = 5) -> list[str]:
        result = await self.session.execute(
            select(ProjectContextEntry)
            .where(
                ProjectContextEntry.project_id == project_id,
                ProjectContextEntry.is_current.is_(True),
                ProjectContextEntry.deleted_at.is_(None),
            )
            .order_by(ProjectContextEntry.updated_at.desc())
            .limit(limit)
        )
        return [truncate(row.content, 400) for row in result.scalars().all()]

    async def _load_notes(self, project_id: UUID, limit: int = 5) -> list[str]:
        result = await self.session.execute(
            select(Note)
            .where(Note.project_id == project_id, Note.deleted_at.is_(None))
            .order_by(Note.updated_at.desc())
            .limit(limit)
        )
        return [f"{n.title or 'Note'}: {truncate(n.content, 200)}" for n in result.scalars().all()]

    async def _load_tasks(self, project_id: UUID, limit: int = 6) -> list[str]:
        result = await self.session.execute(
            select(Task)
            .where(Task.project_id == project_id, Task.deleted_at.is_(None), Task.status != "done")
            .order_by(Task.priority.desc())
            .limit(limit)
        )
        return [f"[{t.priority}] {t.title}" for t in result.scalars().all()]

    async def _load_project_memories(self, user_id: UUID, project_id: UUID, limit: int = 8) -> list[str]:
        result = await self.session.execute(
            select(Memory)
            .where(
                Memory.user_id == user_id,
                Memory.project_id == project_id,
                Memory.deleted_at.is_(None),
                Memory.memory_type.in_(["long_term", "project"]),
            )
            .order_by(Memory.importance.desc(), Memory.updated_at.desc())
            .limit(limit)
        )
        return [m.content for m in result.scalars().all()]

    async def enrich_from_semantic(self, user_id: UUID, project_id: UUID, query: str) -> list[str]:
        """Pull semantically related notes/tasks via embeddings for project continuity."""
        from app.memory.semantic import SemanticRetriever

        hits = await SemanticRetriever(self.session).search(user_id, query, limit=6)
        extras: list[str] = []
        for hit in hits:
            if hit.source_type in ("note", "task", "memory"):
                extras.append(truncate(hit.content, 250))
        return extras[:4]

    async def get_recent_conversation_summaries(self, project_id: UUID, limit: int = 3) -> list[str]:
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.project_id == project_id, Conversation.deleted_at.is_(None), Conversation.summary.isnot(None))
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        return [c.summary for c in result.scalars().all() if c.summary]
