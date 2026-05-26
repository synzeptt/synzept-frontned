"""Subtle task intelligence - suggestions without intrusion."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.service import TaskService


class TaskIntelligence:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.tasks = TaskService(session)

    async def suggestions(self, user_id: UUID, limit: int = 2) -> list[dict]:
        """Light proactive hints for dashboard."""
        open_tasks = [t for t in await self.tasks.list_tasks(user_id) if t.status != "done"]
        if not open_tasks:
            return [
                {
                    "type": "plan",
                    "label": "Set a focus",
                    "description": "Add a task or tell Synzept what you're working on today.",
                }
            ]

        suggestions: list[dict] = []
        now = datetime.now(timezone.utc)
        high = [t for t in open_tasks if t.priority == "high"]
        if len(high) > 3:
            suggestions.append(
                {
                    "type": "prioritize",
                    "label": "Narrow priorities",
                    "description": f"{len(high)} high-priority items are active. Keep one or two in focus today.",
                }
            )

        neglected = []
        for task in open_tasks:
            if not task.updated_at or task.priority == "low":
                continue
            updated_at = task.updated_at
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            if (now - updated_at).days >= 7:
                neglected.append(task)
        if neglected and len(suggestions) < limit:
            suggestions.append(
                {
                    "type": "review",
                    "label": "Review stale tasks",
                    "description": f"'{neglected[0].title}' hasn't been updated in a week.",
                }
            )

        if not suggestions and open_tasks:
            top = sorted(open_tasks, key=lambda t: {"high": 3, "medium": 2, "low": 1}.get(t.priority, 1), reverse=True)
            suggestions.append(
                {
                    "type": "focus",
                    "label": "Suggested focus",
                    "description": f"Start with: {top[0].title}",
                }
            )

        return suggestions[:limit]
