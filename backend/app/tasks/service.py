from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.goal import Milestone
from app.models.goal import Goal
from app.schemas.task import TaskCreate, TaskUpdate

OPEN_STATUSES = {"todo", "in_progress", "pending"}
STATUS_ALIASES = {"pending": "todo", "done": "completed"}


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_tasks(self, user_id: UUID, status: str | None = None, *, project_id: UUID | None = None) -> list[Task]:
        query = select(Task).where(Task.user_id == user_id, Task.deleted_at.is_(None))
        if status:
            status = STATUS_ALIASES.get(status, status)
            query = query.where(Task.status == status)
        if project_id:
            query = query.where(Task.project_id == project_id)
        result = await self.session.execute(query.order_by(Task.created_at.desc()))
        return list(result.scalars().all())

    async def create(self, user_id: UUID, data: TaskCreate) -> Task:
        if data.milestone_id:
            await self._owned_milestone(user_id, data.milestone_id)
        task = Task(
            user_id=user_id,
            title=data.title,
            description=data.description,
            priority=data.priority,
            project_id=data.project_id,
            milestone_id=data.milestone_id,
            due_at=data.due_at,
            status="todo",
        )
        self.session.add(task)
        await self.session.flush()
        await self._record_activity(task, "task_created")
        if task.milestone_id:
            milestone = await self.session.get(Milestone, task.milestone_id)
            if milestone:
                from app.services.goal_progress_service import GoalProgressService

                await GoalProgressService(self.session).recalculate_goal(milestone.goal_id)
        return task

    async def update(self, task_id: UUID, user_id: UUID, data: TaskUpdate) -> Task | None:
        task = await self.session.get(Task, task_id)
        if not task or task.user_id != user_id or task.deleted_at:
            return None
        previous_milestone_id = getattr(task, "milestone_id", None)
        if data.milestone_id:
            await self._owned_milestone(user_id, data.milestone_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "status" and value in STATUS_ALIASES:
                value = STATUS_ALIASES[value]
            setattr(task, field, value)
        await self.session.flush()
        await self.session.refresh(task)
        await self._record_activity(task, "task_completed" if task.status == "completed" else "task_updated")
        affected_milestones = {item for item in (previous_milestone_id, getattr(task, "milestone_id", None)) if item}
        for milestone_id in affected_milestones:
            from app.services.goal_progress_service import GoalProgressService

            milestone = await self.session.get(Milestone, milestone_id)
            if milestone:
                await GoalProgressService(self.session).recalculate_goal(milestone.goal_id)
        return task

    async def soft_delete(self, task_id: UUID, user_id: UUID) -> bool:
        from datetime import datetime, timezone

        task = await self.session.get(Task, task_id)
        if not task or task.user_id != user_id:
            return False
        task.deleted_at = datetime.now(timezone.utc)
        await self._record_activity(task, "task_deleted")
        if getattr(task, "milestone_id", None):
            milestone = await self.session.get(Milestone, task.milestone_id)
            if milestone:
                from app.services.goal_progress_service import GoalProgressService

                await GoalProgressService(self.session).recalculate_goal(milestone.goal_id)
        return True

    async def get_priorities(self, user_id: UUID, limit: int = 6) -> list[Task]:
        tasks = await self.list_tasks(user_id)
        open_tasks = [t for t in tasks if t.status in OPEN_STATUSES]
        weight = {"high": 3, "medium": 2, "low": 1}
        open_tasks.sort(key=lambda t: weight.get(t.priority or "low", 0), reverse=True)
        return open_tasks[:limit]

    async def _record_activity(self, task: Task, action: str) -> None:
        if not hasattr(self.session, "add"):
            return
        from app.services.workspace_activity_service import WorkspaceActivityService

        milestone = await self.session.get(Milestone, task.milestone_id) if getattr(task, "milestone_id", None) else None
        await WorkspaceActivityService(self.session).record(
            user_id=task.user_id,
            action=action,
            title=task.title,
            project_id=task.project_id,
            goal_id=milestone.goal_id if milestone else None,
            task_id=task.id,
        )

    async def _owned_milestone(self, user_id: UUID, milestone_id: UUID) -> Milestone:
        result = await self.session.execute(
            select(Milestone)
            .join(Goal, Goal.id == Milestone.goal_id)
            .where(Milestone.id == milestone_id, Milestone.deleted_at.is_(None), Goal.user_id == user_id)
        )
        milestone = result.scalar_one_or_none()
        if not milestone:
            from app.core.exceptions import NotFoundError

            raise NotFoundError("Milestone not found")
        return milestone
