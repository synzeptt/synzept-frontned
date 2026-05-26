from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectContextOut, ProjectCreate, ProjectOut, ProjectUpdate
from app.workspace.continuity import ProjectContinuityService

router = APIRouter(prefix="/projects")


@router.get("", response_model=list[ProjectOut])
async def list_projects(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(Project).where(Project.user_id == user.id, Project.deleted_at.is_(None)).order_by(Project.updated_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=ProjectOut)
async def create_project(
    body: ProjectCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    project = Project(user_id=user.id, name=body.name, description=body.description)
    session.add(project)
    await session.flush()
    return project


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    project = await session.get(Project, project_id)
    if not project or project.user_id != user.id or project.deleted_at:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id}/context", response_model=ProjectContextOut)
async def get_project_context(
    project_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    context = await ProjectContinuityService(session).restore(user.id, project_id)
    if not context:
        raise HTTPException(status_code=404, detail="Project not found")
    return context


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    project = await session.get(Project, project_id)
    if not project or project.user_id != user.id or project.deleted_at:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await session.flush()
    return project


@router.patch("/{project_id}/archive", response_model=ProjectOut)
async def archive_project(
    project_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    project = await session.get(Project, project_id)
    if not project or project.user_id != user.id or project.deleted_at:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = "archived"
    project.deleted_at = datetime.now(timezone.utc)
    await session.flush()
    return project


@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    project = await session.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = "archived"
    project.deleted_at = datetime.now(timezone.utc)
    return {"ok": True}
