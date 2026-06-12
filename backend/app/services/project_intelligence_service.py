from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.conversation import Conversation
from app.models.memory import Memory
from app.models.note import Note
from app.models.project import Project
from app.models.project_intelligence import ProjectDecision, ProjectIntelligence, ProjectOpenLoop
from app.models.task import Task
from app.schemas.project_intelligence import (
    ProjectActivityOut,
    ProjectDecisionCreate,
    ProjectDecisionUpdate,
    ProjectIntelligencePageOut,
    ProjectIntelligenceUpdate,
    ProjectOpenLoopCreate,
    ProjectOpenLoopUpdate,
    RelatedConversationOut,
    RelatedMemoryOut,
)
from app.tasks.service import OPEN_STATUSES
from app.utils.text import truncate


class ProjectIntelligenceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_page(self, user_id: UUID, project_id: UUID) -> ProjectIntelligencePageOut:
        project = await self._owned_project(user_id, project_id)
        conversations = await self._conversations(user_id, project_id)
        notes = await self._notes(user_id, project_id)
        memories = await self._memories(user_id, project_id)
        tasks = await self._tasks(user_id, project_id)
        decisions = await self._decisions(project_id)
        loops = await self._loops(project_id)
        intelligence = await self._get_or_create_intelligence(project, tasks, decisions, loops)
        activity = self._activity(conversations, notes, memories, tasks)
        last_activity = max(
            [project.updated_at, intelligence.updated_at, *(item.occurred_at for item in activity)],
            key=self._as_utc,
            default=project.updated_at,
        )
        return ProjectIntelligencePageOut(
            project_id=project.id,
            project_name=project.name,
            project_summary=intelligence.summary,
            status=intelligence.status,
            last_activity=last_activity,
            current_focus=intelligence.current_focus,
            recommended_next_step=intelligence.recommended_next_step,
            recent_activity=activity,
            decisions=decisions,
            open_loops=loops,
            conversations=[
                RelatedConversationOut(
                    id=item.id,
                    title=item.title or "Untitled conversation",
                    summary=item.summary or item.active_intent,
                    updated_at=item.updated_at,
                )
                for item in conversations
            ],
            memories=[
                RelatedMemoryOut(
                    id=item.id,
                    title=item.category or item.memory_type,
                    content=item.summary or item.content,
                    updated_at=item.updated_at,
                )
                for item in memories
            ],
            risk=self._risk(project, tasks, decisions, loops),
        )

    async def update_intelligence(
        self,
        user_id: UUID,
        project_id: UUID,
        data: ProjectIntelligenceUpdate,
    ) -> ProjectIntelligence:
        project = await self._owned_project(user_id, project_id)
        intelligence = await self._get_or_create_intelligence(project, [], [], [])
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(intelligence, field, value)
        if data.status is not None:
            project.status = data.status
        await self.session.flush()
        return intelligence

    async def create_decision(self, user_id: UUID, project_id: UUID, data: ProjectDecisionCreate) -> ProjectDecision:
        await self._owned_project(user_id, project_id)
        item = ProjectDecision(project_id=project_id, decision=data.decision.strip())
        self.session.add(item)
        await self.session.flush()
        return item

    async def update_decision(
        self,
        user_id: UUID,
        project_id: UUID,
        decision_id: UUID,
        data: ProjectDecisionUpdate,
    ) -> ProjectDecision:
        await self._owned_project(user_id, project_id)
        result = await self.session.execute(
            select(ProjectDecision).where(ProjectDecision.id == decision_id, ProjectDecision.project_id == project_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("Project decision not found")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(item, field, value.strip() if isinstance(value, str) and field == "decision" else value)
        await self.session.flush()
        return item

    async def create_loop(self, user_id: UUID, project_id: UUID, data: ProjectOpenLoopCreate) -> ProjectOpenLoop:
        await self._owned_project(user_id, project_id)
        item = ProjectOpenLoop(project_id=project_id, loop=data.loop.strip())
        self.session.add(item)
        await self.session.flush()
        return item

    async def update_loop(
        self,
        user_id: UUID,
        project_id: UUID,
        loop_id: UUID,
        data: ProjectOpenLoopUpdate,
    ) -> ProjectOpenLoop:
        await self._owned_project(user_id, project_id)
        result = await self.session.execute(
            select(ProjectOpenLoop).where(ProjectOpenLoop.id == loop_id, ProjectOpenLoop.project_id == project_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("Project open loop not found")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(item, field, value.strip() if isinstance(value, str) and field == "loop" else value)
        await self.session.flush()
        return item

    async def _owned_project(self, user_id: UUID, project_id: UUID) -> Project:
        result = await self.session.execute(
            select(Project).where(Project.id == project_id, Project.user_id == user_id, Project.deleted_at.is_(None))
        )
        project = result.scalar_one_or_none()
        if not project:
            raise NotFoundError("Project not found")
        return project

    async def _get_or_create_intelligence(
        self,
        project: Project,
        tasks: list[Task],
        decisions: list[ProjectDecision],
        loops: list[ProjectOpenLoop],
    ) -> ProjectIntelligence:
        result = await self.session.execute(
            select(ProjectIntelligence).where(ProjectIntelligence.project_id == project.id)
        )
        item = result.scalar_one_or_none()
        if item:
            return item
        open_tasks = [task for task in tasks if task.status in OPEN_STATUSES]
        open_decisions = [decision for decision in decisions if decision.status == "open"]
        open_loops = [loop for loop in loops if loop.status == "open"]
        current_focus = (
            open_loops[0].loop
            if open_loops
            else open_tasks[0].title
            if open_tasks
            else project.description or "Clarify the next important outcome for this project."
        )
        next_step = (
            f"Complete {open_loops[0].loop}."
            if open_loops
            else f"Resolve {open_decisions[0].decision}."
            if open_decisions
            else f"Continue {open_tasks[0].title}."
            if open_tasks
            else f"Define the next concrete action for {project.name}."
        )
        item = ProjectIntelligence(
            project_id=project.id,
            current_focus=current_focus,
            summary=project.context_summary or project.description or f"{project.name} is an active project.",
            recommended_next_step=next_step,
            status=self._normalize_status(project.status),
        )
        try:
            async with self.session.begin_nested():
                self.session.add(item)
                await self.session.flush()
        except IntegrityError:
            result = await self.session.execute(
                select(ProjectIntelligence).where(ProjectIntelligence.project_id == project.id)
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing
            raise
        return item

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
            .limit(10)
        )
        return list(result.scalars())

    async def _notes(self, user_id: UUID, project_id: UUID) -> list[Note]:
        result = await self.session.execute(
            select(Note)
            .where(Note.user_id == user_id, Note.project_id == project_id, Note.deleted_at.is_(None))
            .order_by(Note.updated_at.desc())
            .limit(10)
        )
        return list(result.scalars())

    async def _memories(self, user_id: UUID, project_id: UUID) -> list[Memory]:
        result = await self.session.execute(
            select(Memory)
            .where(Memory.user_id == user_id, Memory.project_id == project_id, Memory.deleted_at.is_(None))
            .order_by(Memory.updated_at.desc())
            .limit(10)
        )
        return list(result.scalars())

    async def _tasks(self, user_id: UUID, project_id: UUID) -> list[Task]:
        result = await self.session.execute(
            select(Task)
            .where(Task.user_id == user_id, Task.project_id == project_id, Task.deleted_at.is_(None))
            .order_by(Task.updated_at.desc())
            .limit(16)
        )
        return list(result.scalars())

    async def _decisions(self, project_id: UUID) -> list[ProjectDecision]:
        result = await self.session.execute(
            select(ProjectDecision).where(ProjectDecision.project_id == project_id).order_by(ProjectDecision.created_at.desc())
        )
        return list(result.scalars())

    async def _loops(self, project_id: UUID) -> list[ProjectOpenLoop]:
        result = await self.session.execute(
            select(ProjectOpenLoop).where(ProjectOpenLoop.project_id == project_id).order_by(ProjectOpenLoop.created_at.desc())
        )
        return list(result.scalars())

    @staticmethod
    def _activity(
        conversations: list[Conversation],
        notes: list[Note],
        memories: list[Memory],
        tasks: list[Task],
    ) -> list[ProjectActivityOut]:
        activity = [
            *[
                ProjectActivityOut(
                    id=item.id,
                    type="conversation",
                    title=item.title or "Untitled conversation",
                    detail=truncate(item.summary or item.active_intent or "", 120) or None,
                    occurred_at=item.updated_at,
                )
                for item in conversations
            ],
            *[
                ProjectActivityOut(
                    id=item.id,
                    type="note",
                    title=item.title or "Untitled note",
                    detail=truncate(item.summary or item.content, 120),
                    occurred_at=item.updated_at,
                )
                for item in notes
            ],
            *[
                ProjectActivityOut(
                    id=item.id,
                    type="memory",
                    title=item.category or item.memory_type,
                    detail=truncate(item.summary or item.content, 120),
                    occurred_at=item.updated_at,
                )
                for item in memories
            ],
            *[
                ProjectActivityOut(
                    id=item.id,
                    type="task",
                    title=item.title,
                    detail=f"Task {item.status.replace('_', ' ')}",
                    occurred_at=item.updated_at,
                )
                for item in tasks
            ],
        ]
        activity.sort(key=lambda item: item.occurred_at, reverse=True)
        return activity[:14]

    @staticmethod
    def _normalize_status(status: str) -> str:
        return status if status in {"active", "paused", "completed"} else "active"

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _risk(project: Project, tasks: list[Task], decisions: list[ProjectDecision], loops: list[ProjectOpenLoop]) -> dict:
        now = datetime.now(timezone.utc)
        updated_at = ProjectIntelligenceService._as_utc(project.updated_at)
        inactive_days = max(0, (now - updated_at).days)
        open_decisions = sum(item.status == "open" for item in decisions)
        open_loops = sum(item.status == "open" for item in loops)
        overdue = sum(
            bool(item.status in OPEN_STATUSES and item.due_at and ProjectIntelligenceService._as_utc(item.due_at) < now)
            for item in tasks
        )
        reasons = []
        if inactive_days >= 7:
            reasons.append(f"This project has had no activity for {inactive_days} days.")
        if open_decisions:
            reasons.append(f"{open_decisions} decision(s) remain unresolved.")
        if open_loops:
            reasons.append(f"{open_loops} open loop(s) remain unfinished.")
        if overdue:
            reasons.append(f"{overdue} overdue task(s) need attention.")
        return {
            "level": "high" if inactive_days >= 14 or overdue else "medium" if reasons else "low",
            "reasons": reasons or ["No immediate risk signals detected."],
        }
