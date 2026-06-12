from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.note import NoteOut
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.workspace import (
    WorkspaceActivityOut,
    WorkspaceInsightOut,
    WorkspaceNoteCreate,
    WorkspaceNoteUpdate,
    WorkspaceOut,
    WorkspaceProjectOut,
    WorkspaceSearchOut,
)
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspace")


@router.get("", response_model=WorkspaceOut)
async def get_workspace(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await WorkspaceService(session).get_workspace(user.id)


@router.get("/search", response_model=WorkspaceSearchOut)
async def search_workspace(
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=40, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await WorkspaceService(session).search(user.id, q, limit=limit)


@router.get("/insights", response_model=list[WorkspaceInsightOut])
async def get_workspace_insights(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await WorkspaceService(session).insights(user.id)


@router.get("/timeline", response_model=list[WorkspaceActivityOut])
async def get_workspace_timeline(
    project_id: UUID | None = None,
    limit: int = Query(default=40, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await WorkspaceService(session).timeline(user.id, project_id=project_id, limit=limit)


@router.post("/projects", response_model=WorkspaceProjectOut)
async def create_project(
    body: ProjectCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await WorkspaceService(session).create_project(user.id, body)


@router.get("/projects/{project_id}", response_model=WorkspaceProjectOut)
async def get_project(
    project_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await WorkspaceService(session).get_project(user.id, project_id)


@router.patch("/projects/{project_id}", response_model=WorkspaceProjectOut)
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await WorkspaceService(session).update_project(user.id, project_id, body)


@router.patch("/projects/{project_id}/archive", response_model=WorkspaceProjectOut)
async def archive_project(
    project_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await WorkspaceService(session).archive_project(user.id, project_id)


@router.get("/notes/search", response_model=list[NoteOut])
async def search_notes(
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=40, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await WorkspaceService(session).search_notes(user.id, q, limit=limit)


@router.post("/notes", response_model=NoteOut)
async def create_note(
    body: WorkspaceNoteCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await WorkspaceService(session).create_note(user.id, body)


@router.patch("/notes/{note_id}", response_model=NoteOut)
async def update_note(
    note_id: UUID,
    body: WorkspaceNoteUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await WorkspaceService(session).update_note(user.id, note_id, body)


@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await WorkspaceService(session).delete_note(user.id, note_id)
    return {"ok": True}
