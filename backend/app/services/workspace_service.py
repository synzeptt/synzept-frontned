from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import String, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.memory.memory_service import MemoryService
from app.models.goal import Goal, Milestone
from app.models.memory import Memory
from app.models.note import Note
from app.models.project import Project
from app.models.task import Task
from app.models.workspace_activity import WorkspaceActivity
from app.schemas.note import NoteCreate, NoteUpdate
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.workspace import (
    WorkspaceActivityOut,
    WorkspaceInsightOut,
    WorkspaceOut,
    WorkspaceProgressOut,
    WorkspaceProjectOut,
    WorkspaceSearchOut,
    WorkspaceSearchResult,
)
from app.services.goal_progress_service import COMPLETED_TASK_STATUSES, GoalProgressService
from app.services.workspace_activity_service import WorkspaceActivityService
from app.tasks.service import OPEN_STATUSES
from app.utils.text import truncate


class WorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.activity = WorkspaceActivityService(session)
        self.goals = GoalProgressService(session)

    async def get_workspace(self, user_id: UUID) -> WorkspaceOut:
        projects = await self._projects(user_id)
        goals = await self.goals.list_goals(user_id)
        tasks = await self._tasks(user_id)
        notes = await self._notes(user_id)
        memories = await MemoryService(self.session).search_memory(user_id=user_id, limit=40)
        return WorkspaceOut(
            projects=[self._project_hub(project, goals, tasks, notes) for project in projects],
            goals=goals,
            tasks=tasks,
            notes=notes,
            memories=memories,
            progress=await self.progress_overview(user_id, projects=projects, goals=goals, tasks=tasks),
            insights=self._insights(projects, goals, tasks),
            recommendations=await self.goals.next_actions(user_id, limit=5),
            timeline=await self.timeline(user_id, limit=20),
        )

    async def get_project(self, user_id: UUID, project_id: UUID) -> WorkspaceProjectOut:
        project = await self._owned_project(user_id, project_id)
        goals = await self.goals.list_goals(user_id)
        tasks = await self._tasks(user_id)
        notes = await self._notes(user_id)
        return self._project_hub(project, goals, tasks, notes)

    async def create_project(self, user_id: UUID, data: ProjectCreate) -> WorkspaceProjectOut:
        project = Project(user_id=user_id, name=data.name, description=data.description)
        self.session.add(project)
        await self.session.flush()
        await self.activity.record(user_id=user_id, action="project_created", title=project.name, project_id=project.id)
        return self._project_hub(project, [], [], [])

    async def update_project(self, user_id: UUID, project_id: UUID, data: ProjectUpdate) -> WorkspaceProjectOut:
        project = await self._owned_project(user_id, project_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        await self.session.flush()
        await self.activity.record(user_id=user_id, action="project_updated", title=project.name, project_id=project.id)
        return await self.get_project(user_id, project.id)

    async def archive_project(self, user_id: UUID, project_id: UUID) -> WorkspaceProjectOut:
        project = await self._owned_project(user_id, project_id)
        project.status = "archived"
        project.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.activity.record(user_id=user_id, action="project_archived", title=project.name, project_id=project.id)
        return self._project_hub(project, [], [], [])

    async def create_note(self, user_id: UUID, data: NoteCreate) -> Note:
        await self._validate_note_links(user_id, project_id=data.project_id, goal_id=data.goal_id)
        note = Note(
            user_id=user_id,
            title=data.title,
            content=data.content,
            summary=data.summary or self._summarize(data.content),
            project_id=data.project_id,
            goal_id=data.goal_id,
            tags=self._clean_tags(data.tags),
        )
        self.session.add(note)
        await self.session.flush()
        await self.activity.record(
            user_id=user_id,
            action="note_created",
            title=note.title or "Untitled note",
            project_id=note.project_id,
            goal_id=note.goal_id,
            note_id=note.id,
        )
        return note

    async def update_note(self, user_id: UUID, note_id: UUID, data: NoteUpdate) -> Note:
        note = await self._owned_note(user_id, note_id)
        values = data.model_dump(exclude_unset=True)
        await self._validate_note_links(
            user_id,
            project_id=values.get("project_id", note.project_id),
            goal_id=values.get("goal_id", note.goal_id),
        )
        for field, value in values.items():
            setattr(note, field, self._clean_tags(value) if field == "tags" and value is not None else value)
        if data.content is not None and data.summary is None:
            note.summary = self._summarize(data.content)
        await self.session.flush()
        await self.activity.record(
            user_id=user_id,
            action="note_updated",
            title=note.title or "Untitled note",
            project_id=note.project_id,
            goal_id=note.goal_id,
            note_id=note.id,
        )
        return note

    async def delete_note(self, user_id: UUID, note_id: UUID) -> None:
        note = await self._owned_note(user_id, note_id)
        note.deleted_at = datetime.now(timezone.utc)
        await self.activity.record(
            user_id=user_id,
            action="note_deleted",
            title=note.title or "Untitled note",
            project_id=note.project_id,
            goal_id=note.goal_id,
            note_id=note.id,
        )

    async def search_notes(self, user_id: UUID, query: str, *, limit: int = 40) -> list[Note]:
        pattern = f"%{query.strip()}%"
        result = await self.session.execute(
            select(Note)
            .where(
                Note.user_id == user_id,
                Note.deleted_at.is_(None),
                or_(Note.title.ilike(pattern), Note.content.ilike(pattern), Note.summary.ilike(pattern), cast(Note.tags, String).ilike(pattern)),
            )
            .order_by(Note.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def search(self, user_id: UUID, query: str, *, limit: int = 40) -> WorkspaceSearchOut:
        pattern = f"%{query.strip()}%"
        project_result = await self.session.execute(
            select(Project).where(
                Project.user_id == user_id,
                Project.deleted_at.is_(None),
                or_(Project.name.ilike(pattern), Project.description.ilike(pattern), Project.context_summary.ilike(pattern)),
            )
        )
        goal_result = await self.session.execute(
            select(Goal).where(
                Goal.user_id == user_id,
                Goal.deleted_at.is_(None),
                or_(Goal.title.ilike(pattern), Goal.description.ilike(pattern)),
            )
        )
        task_result = await self.session.execute(
            select(Task).where(
                Task.user_id == user_id,
                Task.deleted_at.is_(None),
                or_(Task.title.ilike(pattern), Task.description.ilike(pattern)),
            )
        )
        notes = await self.search_notes(user_id, query, limit=limit)
        memories = await MemoryService(self.session).search_memory(user_id=user_id, query=query, limit=limit)
        results = [
            *[
                WorkspaceSearchResult(type="project", id=item.id, title=item.name, detail=item.description or "", project_id=item.id)
                for item in project_result.scalars()
            ],
            *[
                WorkspaceSearchResult(type="goal", id=item.id, title=item.title, detail=item.description, project_id=item.project_id, goal_id=item.id)
                for item in goal_result.scalars()
            ],
            *[
                WorkspaceSearchResult(type="task", id=item.id, title=item.title, detail=item.description or "", project_id=item.project_id)
                for item in task_result.scalars()
            ],
            *[
                WorkspaceSearchResult(type="note", id=item.id, title=item.title or "Untitled note", detail=item.summary or item.content, project_id=item.project_id, goal_id=item.goal_id)
                for item in notes
            ],
            *[
                WorkspaceSearchResult(type="memory", id=item.id, title=item.category or item.memory_type, detail=item.summary or item.content, project_id=item.project_id)
                for item in memories
            ],
        ]
        return WorkspaceSearchOut(query=query, results=results[:limit])

    async def progress_overview(
        self,
        user_id: UUID,
        *,
        projects: list[Project] | None = None,
        goals: list[Goal] | None = None,
        tasks: list[Task] | None = None,
    ) -> WorkspaceProgressOut:
        projects = projects if projects is not None else await self._projects(user_id)
        goals = goals if goals is not None else await self.goals.list_goals(user_id)
        tasks = tasks if tasks is not None else await self._tasks(user_id)
        now = datetime.now(timezone.utc)
        current_start = now - timedelta(days=7)
        previous_start = now - timedelta(days=14)
        current = sum(task.status in COMPLETED_TASK_STATUSES and self._as_utc(task.updated_at) >= current_start for task in tasks)
        previous = sum(
            task.status in COMPLETED_TASK_STATUSES and previous_start <= self._as_utc(task.updated_at) < current_start
            for task in tasks
        )
        return WorkspaceProgressOut(
            goal_completion=self._average([goal.progress for goal in goals]),
            project_completion=self._average([self._project_progress(project.id, goals, tasks) for project in projects]),
            task_completion=self._percentage(sum(task.status in COMPLETED_TASK_STATUSES for task in tasks), len(tasks)),
            weekly_productivity_trend=float(current - previous),
        )

    async def insights(self, user_id: UUID) -> list[WorkspaceInsightOut]:
        return self._insights(await self._projects(user_id), await self.goals.list_goals(user_id), await self._tasks(user_id))

    async def timeline(
        self,
        user_id: UUID,
        *,
        project_id: UUID | None = None,
        limit: int = 40,
    ) -> list[WorkspaceActivityOut]:
        statement = select(WorkspaceActivity).where(WorkspaceActivity.user_id == user_id)
        if project_id:
            statement = statement.where(WorkspaceActivity.project_id == project_id)
        result = await self.session.execute(statement.order_by(WorkspaceActivity.created_at.desc()).limit(limit))
        return [WorkspaceActivityOut.model_validate(item, from_attributes=True) for item in result.scalars()]

    async def _projects(self, user_id: UUID) -> list[Project]:
        result = await self.session.execute(
            select(Project).where(Project.user_id == user_id, Project.deleted_at.is_(None)).order_by(Project.updated_at.desc())
        )
        return list(result.scalars())

    async def _tasks(self, user_id: UUID) -> list[Task]:
        result = await self.session.execute(
            select(Task).where(Task.user_id == user_id, Task.deleted_at.is_(None)).order_by(Task.updated_at.desc())
        )
        return list(result.scalars())

    async def _notes(self, user_id: UUID) -> list[Note]:
        result = await self.session.execute(
            select(Note).where(Note.user_id == user_id, Note.deleted_at.is_(None)).order_by(Note.updated_at.desc())
        )
        return list(result.scalars())

    async def _owned_project(self, user_id: UUID, project_id: UUID) -> Project:
        result = await self.session.execute(
            select(Project).where(Project.id == project_id, Project.user_id == user_id, Project.deleted_at.is_(None))
        )
        project = result.scalar_one_or_none()
        if not project:
            raise NotFoundError("Project not found")
        return project

    async def _owned_note(self, user_id: UUID, note_id: UUID) -> Note:
        result = await self.session.execute(
            select(Note).where(Note.id == note_id, Note.user_id == user_id, Note.deleted_at.is_(None))
        )
        note = result.scalar_one_or_none()
        if not note:
            raise NotFoundError("Note not found")
        return note

    async def _validate_note_links(self, user_id: UUID, *, project_id: UUID | None, goal_id: UUID | None) -> None:
        if project_id:
            await self._owned_project(user_id, project_id)
        if goal_id:
            await self.goals.get_goal(user_id, goal_id)

    def _project_hub(self, project: Project, goals: list[Goal], tasks: list[Task], notes: list[Note]) -> WorkspaceProjectOut:
        linked_goals = [item for item in goals if item.project_id == project.id]
        linked_tasks = [item for item in tasks if item.project_id == project.id]
        linked_notes = [item for item in notes if item.project_id == project.id]
        return WorkspaceProjectOut(
            id=project.id,
            title=project.name,
            description=project.context_summary or project.description or "",
            status=project.status,
            goals=linked_goals,
            tasks=linked_tasks,
            notes=linked_notes,
            progress=self._project_progress(project.id, goals, tasks),
        )

    def _insights(self, projects: list[Project], goals: list[Goal], tasks: list[Task]) -> list[WorkspaceInsightOut]:
        now = datetime.now(timezone.utc)
        insights: list[WorkspaceInsightOut] = []
        for task in tasks:
            if task.status in OPEN_STATUSES and task.due_at and self._as_utc(task.due_at) < now:
                insights.append(WorkspaceInsightOut(type="overdue_task", title=task.title, detail="This task is overdue.", severity="attention", project_id=task.project_id, task_id=task.id))
        for project in projects:
            if project.status == "active" and self._as_utc(project.updated_at) < now - timedelta(days=7):
                insights.append(WorkspaceInsightOut(type="stalled_project", title=project.name, detail="No progress update has been recorded for 7 days.", severity="attention", project_id=project.id))
        for goal in goals:
            if goal.status == "active" and goal.progress == 0:
                insights.append(WorkspaceInsightOut(type="unfinished_goal", title=goal.title, detail="This active goal has not recorded progress yet.", goal_id=goal.id))
        return insights[:12]

    @staticmethod
    def _project_progress(project_id: UUID, goals: list[Goal], tasks: list[Task]) -> float:
        linked_goals = [item.progress for item in goals if item.project_id == project_id]
        if linked_goals:
            return WorkspaceService._average(linked_goals)
        linked_tasks = [item for item in tasks if item.project_id == project_id]
        return WorkspaceService._percentage(sum(item.status in COMPLETED_TASK_STATUSES for item in linked_tasks), len(linked_tasks))

    @staticmethod
    def _average(values: list[float]) -> float:
        return round(sum(values) / len(values), 2) if values else 0.0

    @staticmethod
    def _percentage(completed: int, total: int) -> float:
        return round(completed / total * 100, 2) if total else 0.0

    @staticmethod
    def _clean_tags(tags: list[str]) -> list[str]:
        return list(dict.fromkeys(tag.strip().lower() for tag in tags if tag.strip()))[:20]

    @staticmethod
    def _summarize(content: str) -> str:
        normalized = " ".join(content.split())
        return truncate(normalized, 220)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
