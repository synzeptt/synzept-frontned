from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.project_intelligence import ProjectOpenLoop
from app.models.task import Task
from app.models.user_understanding import UserUnderstanding
from app.tasks.service import OPEN_STATUSES


class PriorityEngine:
    """Ranks priorities from goals, current focus, tasks, projects, and open loops."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def priorities_for_user(self, user_id: UUID, *, limit: int = 6) -> list[dict]:
        rows = await self._understanding_priorities(user_id)
        rows.extend(await self._task_priorities(user_id))
        rows.extend(await self._project_loop_priorities(user_id))
        rows = self._dedupe(rows)
        rows.sort(key=lambda item: (item["score"], item["title"]), reverse=True)
        return rows[:limit]

    async def recommended_next_actions(self, user_id: UUID, *, limit: int = 3) -> list[str]:
        priorities = await self.priorities_for_user(user_id, limit=limit)
        if priorities:
            return [item["action"] for item in priorities]
        return ["Add one current focus so Synzept can recommend the next move."]

    async def _understanding_priorities(self, user_id: UUID) -> list[dict]:
        result = await self.session.execute(
            select(UserUnderstanding).where(
                UserUnderstanding.user_id == user_id,
                UserUnderstanding.category.in_(["current_focus", "open_loops", "short_term_goals", "missions", "priorities", "current_struggles"]),
            )
        )
        weights = {
            "current_focus": 0.92,
            "open_loops": 0.9,
            "priorities": 0.88,
            "current_struggles": 0.84,
            "short_term_goals": 0.8,
            "missions": 0.72,
        }
        return [
            {
                "title": item.value,
                "reason": f"From {item.title}.",
                "action": self._action_for(item.value),
                "source": "understanding",
                "score": weights.get(item.category, 0.65) + min(item.confidence or 0.5, 1.0) * 0.05,
            }
            for item in result.scalars()
            if item.value.strip()
        ]

    async def _task_priorities(self, user_id: UUID) -> list[dict]:
        result = await self.session.execute(
            select(Task)
            .where(Task.user_id == user_id, Task.deleted_at.is_(None), Task.status.in_(OPEN_STATUSES))
            .order_by(Task.updated_at.desc())
            .limit(12)
        )
        weight = {"high": 0.9, "medium": 0.72, "low": 0.56}
        return [
            {
                "title": task.title,
                "reason": task.description or "Open task.",
                "action": f"Continue: {task.title}",
                "source": "task",
                "score": weight.get(task.priority or "medium", 0.7),
            }
            for task in result.scalars()
        ]

    async def _project_loop_priorities(self, user_id: UUID) -> list[dict]:
        result = await self.session.execute(
            select(ProjectOpenLoop, Project.name)
            .join(Project, Project.id == ProjectOpenLoop.project_id)
            .where(Project.user_id == user_id, Project.deleted_at.is_(None), ProjectOpenLoop.status == "open")
            .order_by(ProjectOpenLoop.created_at.desc())
            .limit(12)
        )
        return [
            {
                "title": loop.loop,
                "reason": f"Open loop in {project_name}.",
                "action": f"Resolve: {loop.loop}",
                "source": "project_open_loop",
                "score": 0.86,
            }
            for loop, project_name in result.all()
        ]

    @staticmethod
    def _action_for(title: str) -> str:
        text = title.strip().rstrip(".")
        if not text:
            return "Choose the next concrete step."
        if text.casefold().startswith(("continue", "finish", "review", "ship", "resolve")):
            return text
        return f"Continue: {text}"

    @staticmethod
    def _dedupe(items: list[dict]) -> list[dict]:
        seen: set[str] = set()
        output: list[dict] = []
        for item in items:
            key = " ".join(item["title"].casefold().split())
            if not key or key in seen:
                continue
            seen.add(key)
            output.append(item)
        return output
