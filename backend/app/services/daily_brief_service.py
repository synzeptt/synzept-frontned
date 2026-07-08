from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.daily_brief import DailyBrief
from app.models.memory import Memory
from app.models.project import Project
from app.models.project_intelligence import ProjectIntelligence, ProjectOpenLoop
from app.models.task import Task
from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.services.continuity_assistant_service import ContinuityAssistantService
from app.tasks.service import OPEN_STATUSES
from app.utils.text import truncate


class DailyBriefService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_today(self, user: User, *, refresh: bool = False) -> DailyBrief:
        today = date.today()
        if refresh:
            await self.session.execute(
                delete(DailyBrief).where(DailyBrief.user_id == user.id, DailyBrief.brief_date == today)
            )
        else:
            result = await self.session.execute(
                select(DailyBrief).where(DailyBrief.user_id == user.id, DailyBrief.brief_date == today)
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing

        brief = await self._build(user, today)
        try:
            async with self.session.begin_nested():
                self.session.add(brief)
                await self.session.flush()
        except IntegrityError:
            result = await self.session.execute(
                select(DailyBrief).where(DailyBrief.user_id == user.id, DailyBrief.brief_date == today)
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing
            raise
        return brief

    async def _build(self, user: User, today: date) -> DailyBrief:
        understanding = await self._understanding(user.id)
        projects = await self._active_projects(user.id)
        tasks = await self._tasks(user.id)
        conversations = await self._recent_conversations(user.id)
        memories = await self._memories(user.id)
        project_loops = await self._project_open_loops(user.id)
        project_recommendations = await self._project_recommendations(user.id)

        what_matters = self._what_matters(understanding, projects)
        open_loops = self._open_loops(tasks, conversations, project_loops)
        assistant_recommendation = await ContinuityAssistantService(self.session).recommend_next_step(user.id)
        next_step = assistant_recommendation.detail or self._next_step(open_loops, what_matters, projects, project_recommendations)
        focus_topics = self._focus_topics(understanding, memories, projects)
        recent_progress = self._recent_progress(projects, conversations, tasks)
        communication_style = self._understanding_value(understanding, "Communication Style")
        lead = what_matters[0] if what_matters else "one clear priority"

        return DailyBrief(
            user_id=user.id,
            brief_date=today,
            summary=f"Keep today centered on {lead}.",
            open_loops=open_loops,
            next_step=next_step,
            context={
                "what_matters": what_matters,
                "recent_progress": recent_progress,
                "focus_topics": focus_topics,
                "communication_style": communication_style,
            },
        )

    async def _understanding(self, user_id: UUID) -> list[UserUnderstanding]:
        result = await self.session.execute(
            select(UserUnderstanding)
            .where(UserUnderstanding.user_id == user_id)
            .order_by(UserUnderstanding.updated_at.desc())
        )
        return list(result.scalars())

    async def _active_projects(self, user_id: UUID) -> list[Project]:
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
            .where(Task.user_id == user_id, Task.deleted_at.is_(None))
            .order_by(Task.updated_at.desc())
            .limit(20)
        )
        return list(result.scalars())

    async def _recent_conversations(self, user_id: UUID) -> list[Conversation]:
        since = datetime.now(timezone.utc) - timedelta(days=7)
        result = await self.session.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
                Conversation.archived_at.is_(None),
                Conversation.updated_at >= since,
            )
            .order_by(Conversation.updated_at.desc())
            .limit(6)
        )
        return list(result.scalars())

    async def _memories(self, user_id: UUID) -> list[Memory]:
        result = await self.session.execute(
            select(Memory)
            .where(Memory.user_id == user_id, Memory.deleted_at.is_(None))
            .order_by(Memory.importance_score.desc(), Memory.updated_at.desc())
            .limit(8)
        )
        return list(result.scalars())

    async def _project_open_loops(self, user_id: UUID) -> list[ProjectOpenLoop]:
        result = await self.session.execute(
            select(ProjectOpenLoop)
            .join(Project, Project.id == ProjectOpenLoop.project_id)
            .where(Project.user_id == user_id, Project.deleted_at.is_(None), ProjectOpenLoop.status == "open")
            .order_by(ProjectOpenLoop.created_at.desc())
            .limit(8)
        )
        return list(result.scalars())

    async def _project_recommendations(self, user_id: UUID) -> list[str]:
        result = await self.session.execute(
            select(ProjectIntelligence.recommended_next_step)
            .join(Project, Project.id == ProjectIntelligence.project_id)
            .where(
                Project.user_id == user_id,
                Project.deleted_at.is_(None),
                ProjectIntelligence.status == "active",
                ProjectIntelligence.recommended_next_step != "",
            )
            .order_by(ProjectIntelligence.updated_at.desc())
            .limit(4)
        )
        return list(result.scalars())

    def _what_matters(self, understanding: list[UserUnderstanding], projects: list[Project]) -> list[str]:
        items: list[str] = []
        for title in ("Current Priorities", "Short-Term Goals", "Short-term", "Active Projects", "Long-Term Goals", "Long-term", "Mission"):
            items.extend(self._split_value(self._understanding_value(understanding, title)))
        for category in ("short_term_goals", "long_term_goals", "missions", "current_focus"):
            items.extend(item.value for item in understanding if item.category == category)
        items.extend(project.name for project in projects)
        return self._unique(items)[:6]

    def _open_loops(
        self,
        tasks: list[Task],
        conversations: list[Conversation],
        project_loops: list[ProjectOpenLoop],
    ) -> list[str]:
        loops = [loop.loop for loop in project_loops]
        loops.extend(task.title for task in tasks if task.status in OPEN_STATUSES)
        loops.extend(
            conversation.active_intent
            for conversation in conversations
            if conversation.active_intent
        )
        return self._unique(loops)[:6]

    def _next_step(
        self,
        open_loops: list[str],
        what_matters: list[str],
        projects: list[Project],
        project_recommendations: list[str],
    ) -> str:
        if project_recommendations:
            return project_recommendations[0]
        if open_loops:
            return f"Continue {open_loops[0]}."
        if what_matters:
            return f"Set aside focused time for {what_matters[0]}."
        if projects:
            return f"Choose the next concrete action for {projects[0].name}."
        return "Choose one meaningful priority for today."

    def _focus_topics(
        self,
        understanding: list[UserUnderstanding],
        memories: list[Memory],
        projects: list[Project],
    ) -> list[str]:
        topics: list[str] = []
        for item in understanding:
            if item.category == "learned_insights" or item.title in {"Interests", "Current Learning Areas"}:
                topics.extend(self._split_value(item.value))
        topics.extend(memory.summary or memory.content for memory in memories)
        topics.extend(project.name for project in projects)
        return [truncate(topic, 90) for topic in self._unique(topics)[:6]]

    def _recent_progress(
        self,
        projects: list[Project],
        conversations: list[Conversation],
        tasks: list[Task],
    ) -> list[dict]:
        items: list[tuple[datetime, dict]] = []
        for project in projects[:4]:
            items.append((project.updated_at, {"type": "project", "title": project.name, "detail": "Project updated"}))
        for conversation in conversations[:4]:
            items.append(
                (
                    conversation.updated_at,
                    {
                        "type": "conversation",
                        "title": conversation.title or "Recent conversation",
                        "detail": truncate(conversation.summary or conversation.active_intent or "", 100) or None,
                    },
                )
            )
        for task in tasks:
            if task.status in {"completed", "done"}:
                items.append((task.updated_at, {"type": "task", "title": task.title, "detail": "Completed task"}))
        items.sort(key=lambda entry: entry[0], reverse=True)
        return [item for _, item in items[:6]]

    @staticmethod
    def _understanding_value(understanding: list[UserUnderstanding], title: str) -> str | None:
        item = next((item for item in understanding if item.title == title), None)
        return item.value if item else None

    @staticmethod
    def _split_value(value: str | None) -> list[str]:
        if not value:
            return []
        lines = value.replace(";", "\n").splitlines()
        return [line.strip(" -*\t") for line in lines if line.strip(" -*\t")]

    @staticmethod
    def _unique(items) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in items:
            normalized = item.strip()
            key = normalized.casefold()
            if normalized and key not in seen:
                seen.add(key)
                result.append(normalized)
        return result
