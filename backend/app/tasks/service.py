from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
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
        task = Task(
            user_id=user_id,
            title=data.title,
            description=data.description,
            priority=data.priority,
            project_id=data.project_id,
            due_at=data.due_at,
            status="todo",
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def update(self, task_id: UUID, user_id: UUID, data: TaskUpdate) -> Task | None:
        task = await self.session.get(Task, task_id)
        if not task or task.user_id != user_id or task.deleted_at:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "status" and value in STATUS_ALIASES:
                value = STATUS_ALIASES[value]
            setattr(task, field, value)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def soft_delete(self, task_id: UUID, user_id: UUID) -> bool:
        from datetime import datetime, timezone

        task = await self.session.get(Task, task_id)
        if not task or task.user_id != user_id:
            return False
        task.deleted_at = datetime.now(timezone.utc)
        return True

    async def get_priorities(self, user_id: UUID, limit: int = 6) -> list[Task]:
        tasks = await self.list_tasks(user_id)
        open_tasks = [t for t in tasks if t.status in OPEN_STATUSES]
        weight = {"high": 3, "medium": 2, "low": 1}
        open_tasks.sort(key=lambda t: weight.get(t.priority or "low", 0), reverse=True)
        return open_tasks[:limit]
