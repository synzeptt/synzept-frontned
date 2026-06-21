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


EMPTY_MISSION = "Add a mission in Synzept Knows You so Home can hold your north star."
EMPTY_FOCUS = "Choose the one thing that matters most right now."


class S1HomeService:
    """Fast Home read model: Knows You plus the smallest useful work context."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_home(self, user: User) -> S1HomeOut:
        profile = await UserUnderstandingService(self.session).profile_for_user(user)
        projects_result = await self.session.execute(
            select(Project)
            .where(Project.user_id == user.id, Project.deleted_at.is_(None), Project.status == "active")
            .order_by(Project.updated_at.desc())
            .limit(3)
        )
        projects = list(projects_result.scalars())
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
        active_project = projects[0] if projects else None
        mission = self._first(profile.current_mission) or (active_project.description if active_project else "")
        mission = mission or EMPTY_MISSION
        focus = (
            self._first(profile.current_focus)
            or (active_project.current_focus if active_project else "")
            or (active_project.recommended_next_step if active_project else "")
            or (tasks[0].title if tasks else "")
            or EMPTY_FOCUS
        )
        open_loops = [
            S1ContextItem(id=f"knows-you-{index}", title=item, detail="Saved in Synzept Knows You", href="/knows-you", priority="high", source="knows_you")
            for index, item in enumerate(profile.open_loops[:3])
        ]
        open_loops.extend(
            S1ContextItem(id=str(task.id), title=task.title, detail=task.description or "Unfinished task", href="/tasks", priority=task.priority or "medium", source="task")
            for task in tasks
        )
        open_loops.extend(
            S1ContextItem(id=str(loop.id), title=loop.loop, detail=f"Open loop in {project_name}", href=f"/projects/{loop.project_id}", priority="high", source="project_open_loop")
            for loop, project_name in loops
        )
        open_loops = self._unique(open_loops)[:5]
        last_time = [
            S1ContextItem(
                id=str(project.id),
                title=project.name,
                detail=project.current_focus or project.recommended_next_step or project.description or "Active project",
                href=f"/projects/{project.id}",
                priority="medium",
                source="project",
            )
            for project in projects
        ]
        lead = open_loops[0] if open_loops else None
        learned_action = self._first(profile.next_suggested_actions)
        action = S1RecommendedAction(
            title=learned_action or (lead.title if lead else focus),
            reason=(
                "Suggested from Synzept Knows You."
                if learned_action
                else lead.detail
                if lead
                else "Start with one clear focus so Synzept can preserve continuity."
            ),
            href="/knows-you" if learned_action else ((lead.href or "/chat") if lead else "/chat"),
        )
        home = S1HomeContext(
            greeting=f"Welcome back{', ' + user.display_name if user.display_name else ''}.",
            mission=mission,
            focus=focus,
            last_time=last_time,
            open_loops=open_loops,
            suggested_next_action=action,
        )
        prompt = "\n".join([
            "Continue working from my Synzept Home.", "", f"Mission: {mission}", f"Current Focus: {focus}",
            "Open Loops: " + ("; ".join(item.title for item in open_loops) or "None visible"),
            f"Suggested Next Action: {action.title}", "", "Do not ask me to re-explain. Help me continue from this context.",
        ])
        return S1HomeOut(
            generated_at=datetime.now(timezone.utc),
            home=home,
            continue_prompt=prompt,
            context_sources={
                "understanding": len(profile.current_mission) + len(profile.current_focus) + len(profile.open_loops) + len(profile.next_suggested_actions),
                "projects": len(projects),
                "tasks": len(tasks),
                "open_loops": len(loops),
            },
        )

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
