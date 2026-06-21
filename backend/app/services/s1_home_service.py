from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.project_intelligence import ProjectOpenLoop
from app.models.task import Task
from app.models.user import User
from app.schemas.s1 import S1ContextItem, S1HomeContext, S1HomeOut, S1RecommendedAction
from app.services.user_understanding_service import UserUnderstandingService
from app.tasks.service import OPEN_STATUSES


class S1HomeService:
    """Fast Home read model: Knows You plus the smallest useful work context."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_home(self, user: User) -> S1HomeOut:
        profile = await UserUnderstandingService(self.session).profile_for_user(user)
        tasks_result = await self.session.execute(
            select(Task).where(Task.user_id == user.id, Task.deleted_at.is_(None), Task.status.in_(OPEN_STATUSES)).order_by(Task.updated_at.desc()).limit(4)
        )
        tasks = list(tasks_result.scalars())
        loops_result = await self.session.execute(
            select(ProjectOpenLoop, Project.name)
            .join(Project, Project.id == ProjectOpenLoop.project_id)
            .where(Project.user_id == user.id, Project.deleted_at.is_(None), ProjectOpenLoop.status == "open")
            .order_by(ProjectOpenLoop.created_at.desc()).limit(4)
        )
        loops = list(loops_result.all())
        mission = self._first(profile.current_mission) or "Add a mission in Synzept Knows You."
        focus = self._first(profile.current_focus) or (tasks[0].title if tasks else "Choose the one thing that matters most right now.")
        open_loops = [
            S1ContextItem(id=str(task.id), title=task.title, detail=task.description or "Unfinished task", href="/tasks", priority=task.priority or "medium", source="task")
            for task in tasks
        ]
        open_loops.extend(
            S1ContextItem(id=str(loop.id), title=loop.loop, detail=f"Open loop in {project_name}", href=f"/projects/{loop.project_id}", priority="high", source="project_open_loop")
            for loop, project_name in loops
        )
        open_loops = self._unique(open_loops)[:5]
        lead = open_loops[0] if open_loops else None
        action = S1RecommendedAction(
            title=lead.title if lead else focus,
            reason=lead.detail if lead else "Start with one clear focus so Synzept can preserve continuity.",
            href=lead.href or "/chat" if lead else "/chat",
        )
        home = S1HomeContext(
            greeting=f"Welcome back{', ' + user.display_name if user.display_name else ''}.",
            mission=mission,
            focus=focus,
            open_loops=open_loops,
            suggested_next_action=action,
        )
        prompt = "\n".join([
            "Continue working from my Synzept Home.", "", f"Mission: {mission}", f"Current Focus: {focus}",
            "Open Loops: " + ("; ".join(item.title for item in open_loops) or "None visible"),
            f"Suggested Next Action: {action.title}", "", "Do not ask me to re-explain. Help me continue from this context.",
        ])
        return S1HomeOut(generated_at=datetime.now(timezone.utc), home=home, continue_prompt=prompt, context_sources={"understanding": len(profile.current_mission) + len(profile.current_focus), "tasks": len(tasks), "open_loops": len(loops)})

    @staticmethod
    def _first(values: list[str]) -> str:
        return values[0] if values else ""

    @staticmethod
    def _unique(items: list[S1ContextItem]) -> list[S1ContextItem]:
        seen: set[str] = set()
        output: list[S1ContextItem] = []
        for item in items:
            key = item.title.casefold()
            if key and key not in seen:
                seen.add(key)
                output.append(item)
        return output
