"""Project detection and compact project context retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.project import Project
from app.models.task import Task
from app.utils.text import tokenize, truncate


@dataclass(slots=True)
class ProjectContextBundle:
    project_id: UUID | None = None
    name: str = ""
    summary: str = ""
    active_tasks: list[str] = field(default_factory=list)


class ProjectContextService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def detect_project(
        self,
        *,
        user_id: UUID,
        message: str,
        explicit_project_id: UUID | None = None,
        conversation: Conversation | None = None,
    ) -> UUID | None:
        if explicit_project_id:
            project = await self.session.get(Project, explicit_project_id)
            if project and project.user_id == user_id and not project.deleted_at:
                return project.id
        if conversation and conversation.project_id:
            return conversation.project_id

        lower = message.lower()
        projects = await self._active_projects(user_id)
        for project in projects:
            if project.name.lower() in lower:
                return project.id

        message_tokens = set(tokenize(lower))
        best: tuple[int, UUID] | None = None
        for project in projects:
            haystack = " ".join([project.name, project.description or "", project.context_summary or ""])
            overlap = len(message_tokens & set(tokenize(haystack)))
            if overlap and (best is None or overlap > best[0]):
                best = (overlap, project.id)
        return best[1] if best else None

    async def get_context(
        self,
        *,
        user_id: UUID,
        project_id: UUID | None,
        include_tasks: bool = True,
    ) -> ProjectContextBundle:
        if not project_id:
            return ProjectContextBundle()
        project = await self.session.get(Project, project_id)
        if not project or project.user_id != user_id or project.deleted_at:
            return ProjectContextBundle()

        tasks: list[str] = []
        if include_tasks:
            result = await self.session.execute(
                select(Task)
                .where(
                    Task.user_id == user_id,
                    Task.project_id == project_id,
                    Task.deleted_at.is_(None),
                    Task.status.in_(["pending", "in_progress"]),
                )
                .order_by(Task.priority.desc(), Task.updated_at.desc())
                .limit(8)
            )
            tasks = [truncate(f"{task.title} ({task.priority})", 180) for task in result.scalars().all()]

        summary = "\n".join(part for part in [project.description, project.context_summary] if part)
        return ProjectContextBundle(
            project_id=project.id,
            name=project.name,
            summary=truncate(summary, 1200),
            active_tasks=tasks,
        )

    async def _active_projects(self, user_id: UUID) -> list[Project]:
        result = await self.session.execute(
            select(Project).where(
                Project.user_id == user_id,
                Project.deleted_at.is_(None),
                Project.status == "active",
            )
        )
        return list(result.scalars().all())
