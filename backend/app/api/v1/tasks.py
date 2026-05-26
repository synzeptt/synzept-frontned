from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate
from app.tasks.service import TaskService

router = APIRouter(prefix="/tasks")


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    status: str | None = None,
    project_id: UUID | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await TaskService(session).list_tasks(user.id, status, project_id=project_id)


@router.post("", response_model=TaskOut)
async def create_task(
    body: TaskCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await TaskService(session).create(user.id, body)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: UUID,
    body: TaskUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    task = await TaskService(session).update(task_id, user.id, body)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}")
async def delete_task(
    task_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    ok = await TaskService(session).soft_delete(task_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"ok": True}
