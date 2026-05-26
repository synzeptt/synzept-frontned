"""Project continuity restoration across conversations, notes, tasks, and memories."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.memory import Memory
from app.models.note import Note
from app.models.project import Project
from app.models.task import Task
from app.schemas.project import ProjectContextOut


OPEN_TASK_STATUSES = ("todo", "in_progress", "pending")


class ProjectContinuityService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def restore(self, user_id: UUID, project_id: UUID) -> ProjectContextOut | None:
        project = await self.session.get(Project, project_id)
        if not project or project.user_id != user_id or project.deleted_at:
            return None

        conversations = await self._conversations(user_id, project_id)
        notes = await self._notes(user_id, project_id)
        tasks = await self._tasks(user_id, project_id)
        memories = await self._memories(user_id, project_id)
        summary = self._continuity_summary(project, conversations, notes, tasks, memories)

        return ProjectContextOut(
            project=project,
            conversations=conversations,
            notes=notes,
            tasks=tasks,
            memories=memories,
            continuity_summary=summary,
        )

    async def _conversations(self, user_id: UUID, project_id: UUID) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.project_id == project_id,
                Conversation.deleted_at.is_(None),
                Conversation.archived_at.is_(None),
            )
            .order_by(Conversation.updated_at.desc())
            .limit(12)
        )
        return list(result.scalars().all())

    async def _notes(self, user_id: UUID, project_id: UUID) -> list[Note]:
        result = await self.session.execute(
            select(Note)
            .where(Note.user_id == user_id, Note.project_id == project_id, Note.deleted_at.is_(None))
            .order_by(Note.updated_at.desc())
            .limit(12)
        )
        return list(result.scalars().all())

    async def _tasks(self, user_id: UUID, project_id: UUID) -> list[Task]:
        result = await self.session.execute(
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.project_id == project_id,
                Task.deleted_at.is_(None),
                Task.status.in_(OPEN_TASK_STATUSES),
            )
            .order_by(Task.priority.desc(), Task.updated_at.desc())
            .limit(12)
        )
        return list(result.scalars().all())

    async def _memories(self, user_id: UUID, project_id: UUID) -> list[Memory]:
        result = await self.session.execute(
            select(Memory)
            .where(
                Memory.user_id == user_id,
                Memory.project_id == project_id,
                Memory.deleted_at.is_(None),
            )
            .order_by(Memory.importance_score.desc(), Memory.updated_at.desc())
            .limit(8)
        )
        return list(result.scalars().all())

    @staticmethod
    def _continuity_summary(
        project: Project,
        conversations: list[Conversation],
        notes: list[Note],
        tasks: list[Task],
        memories: list[Memory],
    ) -> str:
        parts: list[str] = []
        if project.context_summary:
            parts.append(project.context_summary)
        elif project.description:
            parts.append(project.description)
        if conversations:
            parts.append(f"Recent conversations: {', '.join((c.title or 'Untitled') for c in conversations[:3])}.")
        if tasks:
            parts.append(f"Open tasks: {', '.join(t.title for t in tasks[:4])}.")
        if notes:
            parts.append(f"Recent notes: {', '.join((n.title or n.summary or 'Untitled') for n in notes[:3])}.")
        if memories:
            parts.append(f"Relevant context: {', '.join((m.summary or m.content) for m in memories[:2])}.")
        return " ".join(parts) or "No continuity context has been built for this project yet."
