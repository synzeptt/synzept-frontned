from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.engine import MemoryEngine
from app.models.conversation import Conversation
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.schemas.continue_context import ContinueContextCardOut, ContinueContextOut
from app.services.open_loops_engine_service import OpenLoopsEngineService
from app.tasks.service import OPEN_STATUSES
from app.utils.text import truncate


class ContinueContextService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_context(self, user: User) -> ContinueContextOut:
        projects = await self._projects(user.id)
        conversations = await self._conversations(user.id)
        tasks = await self._tasks(user.id)
        understanding = await self._understanding(user.id)
        memories = await MemoryEngine(self.session).store.list_for_user(user.id, limit=8)
        open_loop_engine = await OpenLoopsEngineService(self.session).list(user.id)

        mission = self._understanding_value(understanding, "current_mission") or self._understanding_value(understanding, "missions") or self._project_value(projects, "description") or "Build a clear continuity system for the work that matters."
        focus = self._understanding_value(understanding, "current_focus") or self._project_value(projects, "current_focus") or self._task_value(tasks) or "Choose the next meaningful action."
        suggested_action = self._understanding_value(understanding, "next_suggested_actions") or self._project_value(projects, "recommended_next_step") or focus
        memory_context = [truncate(item.summary or item.content, 160) for item in memories[:5]]
        open_loops = [item.title for item in open_loop_engine.items[:5]]
        recent_threads = [conversation.title or conversation.summary or "Recent conversation" for conversation in conversations[:5]]

        shared_context = {
            "current_mission": mission,
            "current_focus": focus,
            "suggested_next_action": suggested_action,
            "memory": memory_context,
            "open_loops": open_loops,
            "user_understanding": [item.value for item in understanding[:6]],
            "recent_conversations": recent_threads,
        }

        active_project = projects[0] if projects else None
        active_task = next((task for task in tasks if task.status in OPEN_STATUSES), None)
        recent_conversation = conversations[0] if conversations else None

        cards = [
            self._card(
                kind="synzept",
                title="Continue Current Focus",
                last_activity=self._last_activity([*projects[:1], *conversations[:1], *tasks[:1]]),
                status=focus,
                context=shared_context,
                intent="Continue my current focus. Start by restoring the full continuity context, then recommend the next concrete move.",
                project=active_project,
            ),
            self._card(
                kind="project",
                title=f"Continue {active_project.name}" if active_project else "Continue Current Project",
                last_activity=self._last_activity([active_project] if active_project else []),
                status=(active_project.current_focus or active_project.recommended_next_step or active_project.description) if active_project else "No active project yet",
                context=shared_context,
                intent="Continue the current project. Use memory, open loops, user understanding, recent conversations, current focus, and suggested next action.",
                project=active_project,
            ),
            self._card(
                kind="goal",
                title="Continue Personal Goal",
                last_activity=self._last_activity([active_task] if active_task else []),
                status=active_task.title if active_task else mission,
                context=shared_context,
                intent="Continue the most important personal goal. Identify what matters now and the smallest useful next action.",
                project=active_project,
            ),
            self._card(
                kind="recent",
                title=f"Continue {recent_conversation.title}" if recent_conversation and recent_conversation.title else "Continue Recent Work",
                last_activity=self._last_activity([recent_conversation] if recent_conversation else []),
                status=(recent_conversation.summary or recent_conversation.active_intent) if recent_conversation else suggested_action,
                context=shared_context,
                intent="Continue the recent work thread without asking me to re-explain context.",
                project=active_project,
            ),
        ]

        return ContinueContextOut(
            headline=f"Welcome back{', ' + user.display_name if user.display_name else ''}.",
            summary="Last activity, unfinished work, and the clearest next move are ready.",
            last_activity=recent_threads[:5] or [self._project_value(projects, "name") or focus],
            open_loops=open_loops,
            suggested_next_action=suggested_action,
            cards=cards,
            context_used={
                "memories": len(memory_context),
                "open_loops": len(open_loops),
                "understanding": len(understanding),
                "recent_conversations": len(recent_threads),
                "projects": len(projects),
            },
        )

    async def _projects(self, user_id) -> list[Project]:
        result = await self.session.execute(
            select(Project)
            .where(Project.user_id == user_id, Project.deleted_at.is_(None), Project.status != "archived")
            .order_by(Project.updated_at.desc())
            .limit(8)
        )
        return list(result.scalars().all())

    async def _conversations(self, user_id) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None), Conversation.archived_at.is_(None))
            .order_by(Conversation.updated_at.desc())
            .limit(8)
        )
        return list(result.scalars().all())

    async def _tasks(self, user_id) -> list[Task]:
        result = await self.session.execute(
            select(Task)
            .where(Task.user_id == user_id, Task.deleted_at.is_(None))
            .order_by(Task.updated_at.desc())
            .limit(12)
        )
        return list(result.scalars().all())

    async def _understanding(self, user_id) -> list[UserUnderstanding]:
        result = await self.session.execute(
            select(UserUnderstanding)
            .where(UserUnderstanding.user_id == user_id)
            .order_by(UserUnderstanding.updated_at.desc())
            .limit(20)
        )
        return list(result.scalars().all())

    def _card(self, *, kind: str, title: str, last_activity: str, status: str, context: dict, intent: str, project: Project | None) -> ContinueContextCardOut:
        prompt = "\n".join(
            [
                intent,
                "",
                "Loaded continuity context:",
                f"- Current mission: {context['current_mission']}",
                f"- Current focus: {context['current_focus']}",
                f"- Suggested next action: {context['suggested_next_action']}",
                "- Open loops: " + self._join(context["open_loops"]),
                "- Memory: " + self._join(context["memory"]),
                "- User understanding: " + self._join(context["user_understanding"]),
                "- Recent conversations: " + self._join(context["recent_conversations"]),
                "",
                "Do not ask me to re-explain. Start from this context and help me continue.",
            ]
        )
        return ContinueContextCardOut(
            id=kind,
            kind=kind,
            title=title,
            last_activity=last_activity,
            current_status=truncate(status or "Ready to continue", 180),
            continue_label="Continue",
            project_id=str(project.id) if project else None,
            prompt=prompt,
        )

    @staticmethod
    def _understanding_value(items: list[UserUnderstanding], category: str) -> str:
        item = next((row for row in items if row.category == category), None)
        return truncate(item.value, 240) if item else ""

    @staticmethod
    def _project_value(projects: list[Project], field: str) -> str:
        for project in projects:
            value = getattr(project, field, None)
            if value:
                return truncate(value, 240)
        return ""

    @staticmethod
    def _task_value(tasks: list[Task]) -> str:
        task = next((item for item in tasks if item.status in OPEN_STATUSES), None)
        return task.title if task else ""

    @staticmethod
    def _last_activity(items: list) -> str:
        dates = [getattr(item, "updated_at", None) or getattr(item, "created_at", None) for item in items if item]
        dates = [item for item in dates if item]
        if not dates:
            return "No recent activity yet"
        last = max(dates)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        days = max((datetime.now(timezone.utc) - last).days, 0)
        if days == 0:
            return "Today"
        if days == 1:
            return "Yesterday"
        return f"{days} days ago"

    @staticmethod
    def _join(items: list[str]) -> str:
        cleaned = [truncate(item, 140) for item in items if item]
        return "; ".join(cleaned[:5]) if cleaned else "Nothing explicit yet"
