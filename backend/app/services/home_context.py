from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.daily_brief_phase8 import DailyBriefSnapshot
from app.models.daily_summary import DailySummary
from app.models.memory import Memory
from app.models.project import Project
from app.models.project_intelligence import ProjectDecision, ProjectOpenLoop
from app.models.project_intelligence_phase2 import Decision
from app.models.task import Task
from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.schemas.user_understanding import UserUnderstandingProfileOut
from app.services.user_understanding_service import UserUnderstandingService
from app.tasks.service import OPEN_STATUSES


@dataclass(slots=True)
class HomeContext:
    user: User
    profile: UserUnderstandingProfileOut
    understanding: list[UserUnderstanding] = field(default_factory=list)
    memories: list[Memory] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    conversations: list[Conversation] = field(default_factory=list)
    daily_summaries: list[DailySummary] = field(default_factory=list)
    daily_brief: DailyBriefSnapshot | None = None
    project_open_loops: list[tuple[ProjectOpenLoop, str]] = field(default_factory=list)
    project_decisions: list[tuple[ProjectDecision, str]] = field(default_factory=list)
    decisions: list[tuple[Decision, str]] = field(default_factory=list)


class HomeContextService:
    """Loads the small, bounded context needed to generate Home."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load(self, user: User) -> HomeContext:
        profile = await UserUnderstandingService(self.session).profile_for_user(user)
        understanding = await self._understanding(user.id)
        projects = await self._projects(user.id)
        tasks = await self._tasks(user.id)
        conversations = await self._conversations(user.id)
        memories = await self._memories(user.id)
        daily_summaries = await self._daily_summaries(user.id)
        daily_brief = await self._daily_brief(user.id)
        return HomeContext(
            user=user,
            profile=profile,
            understanding=understanding,
            memories=memories,
            projects=projects,
            tasks=tasks,
            conversations=conversations,
            daily_summaries=daily_summaries,
            daily_brief=daily_brief,
            project_open_loops=await self._project_open_loops(user.id),
            project_decisions=await self._project_decisions(user.id),
            decisions=await self._decisions(user.id),
        )

    async def _understanding(self, user_id: UUID) -> list[UserUnderstanding]:
        result = await self.session.execute(
            select(UserUnderstanding).where(UserUnderstanding.user_id == user_id).order_by(UserUnderstanding.updated_at.desc()).limit(80)
        )
        return list(result.scalars())

    async def _memories(self, user_id: UUID) -> list[Memory]:
        result = await self.session.execute(
            select(Memory)
            .where(Memory.user_id == user_id, Memory.deleted_at.is_(None))
            .order_by(Memory.importance_score.desc(), Memory.updated_at.desc())
            .limit(30)
        )
        return list(result.scalars())

    async def _projects(self, user_id: UUID) -> list[Project]:
        result = await self.session.execute(
            select(Project)
            .where(Project.user_id == user_id, Project.deleted_at.is_(None), Project.status != "archived")
            .order_by(Project.updated_at.desc())
            .limit(8)
        )
        return list(result.scalars())

    async def _tasks(self, user_id: UUID) -> list[Task]:
        result = await self.session.execute(
            select(Task)
            .where(Task.user_id == user_id, Task.deleted_at.is_(None), Task.status.in_(OPEN_STATUSES))
            .order_by(Task.updated_at.desc())
            .limit(12)
        )
        return list(result.scalars())

    async def _conversations(self, user_id: UUID) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None), Conversation.archived_at.is_(None))
            .order_by(Conversation.updated_at.desc())
            .limit(8)
        )
        return list(result.scalars())

    async def _daily_summaries(self, user_id: UUID) -> list[DailySummary]:
        since = date.today() - timedelta(days=7)
        result = await self.session.execute(
            select(DailySummary)
            .where(DailySummary.user_id == user_id, DailySummary.summary_date >= since)
            .order_by(DailySummary.summary_date.desc(), DailySummary.updated_at.desc())
            .limit(6)
        )
        return list(result.scalars())

    async def _daily_brief(self, user_id: UUID) -> DailyBriefSnapshot | None:
        result = await self.session.execute(
            select(DailyBriefSnapshot)
            .where(DailyBriefSnapshot.user_id == user_id)
            .order_by(DailyBriefSnapshot.brief_date.desc(), DailyBriefSnapshot.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _project_open_loops(self, user_id: UUID) -> list[tuple[ProjectOpenLoop, str]]:
        result = await self.session.execute(
            select(ProjectOpenLoop, Project.name)
            .join(Project, Project.id == ProjectOpenLoop.project_id)
            .where(Project.user_id == user_id, Project.deleted_at.is_(None), ProjectOpenLoop.status == "open")
            .order_by(ProjectOpenLoop.created_at.desc())
            .limit(8)
        )
        return list(result.all())

    async def _project_decisions(self, user_id: UUID) -> list[tuple[ProjectDecision, str]]:
        result = await self.session.execute(
            select(ProjectDecision, Project.name)
            .join(Project, Project.id == ProjectDecision.project_id)
            .where(Project.user_id == user_id, Project.deleted_at.is_(None), ProjectDecision.status == "open")
            .order_by(ProjectDecision.created_at.desc())
            .limit(8)
        )
        return list(result.all())

    async def _decisions(self, user_id: UUID) -> list[tuple[Decision, str]]:
        result = await self.session.execute(
            select(Decision, Project.name)
            .join(Project, Project.id == Decision.project_id)
            .where(Project.user_id == user_id, Project.deleted_at.is_(None))
            .order_by(Decision.updated_at.desc())
            .limit(8)
        )
        return list(result.all())
