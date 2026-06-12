from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.note import Note
from app.models.user import User
from app.schemas.note import NoteCreate, NoteOut, NoteUpdate
from app.services.embedding_service import EmbeddingService
from app.services.workspace_activity_service import WorkspaceActivityService

router = APIRouter(prefix="/notes")


@router.get("", response_model=list[NoteOut])
async def list_notes(
    project_id: UUID | None = None,
    q: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    query = select(Note).where(Note.user_id == user.id, Note.deleted_at.is_(None))
    if project_id:
        query = query.where(Note.project_id == project_id)
    if q:
        pattern = f"%{q}%"
        query = query.where((Note.title.ilike(pattern)) | (Note.content.ilike(pattern)) | (Note.summary.ilike(pattern)))
    result = await session.execute(query.order_by(Note.updated_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=NoteOut)
async def create_note(
    body: NoteCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    note = Note(
        user_id=user.id,
        title=body.title,
        content=body.content,
        project_id=body.project_id,
        goal_id=body.goal_id,
        tags=body.tags,
        summary=body.summary or _summarize_note(body.content),
    )
    session.add(note)
    await session.flush()
    try:
        emb = EmbeddingService()
        await emb.upsert(
            session,
            user_id=user.id,
            source_type="note",
            source_id=note.id,
            content=f"{body.title or ''}\n{body.content}".strip(),
        )
    except Exception:
        pass
    await WorkspaceActivityService(session).record(
        user_id=user.id, action="note_created", title=note.title or "Untitled note", project_id=note.project_id, goal_id=note.goal_id, note_id=note.id
    )
    return note


@router.patch("/{note_id}", response_model=NoteOut)
async def update_note(
    note_id: UUID,
    body: NoteUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    note = await session.get(Note, note_id)
    if not note or note.user_id != user.id or note.deleted_at:
        raise HTTPException(status_code=404, detail="Note not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    if body.content is not None and body.summary is None:
        note.summary = _summarize_note(body.content)
    await session.flush()
    await WorkspaceActivityService(session).record(
        user_id=user.id, action="note_updated", title=note.title or "Untitled note", project_id=note.project_id, goal_id=note.goal_id, note_id=note.id
    )
    return note


@router.delete("/{note_id}")
async def delete_note(
    note_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    note = await session.get(Note, note_id)
    if not note or note.user_id != user.id:
        raise HTTPException(status_code=404, detail="Note not found")
    note.deleted_at = datetime.now(timezone.utc)
    await WorkspaceActivityService(session).record(
        user_id=user.id, action="note_deleted", title=note.title or "Untitled note", project_id=note.project_id, goal_id=note.goal_id, note_id=note.id
    )
    return {"ok": True}


def _summarize_note(content: str) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= 220:
        return normalized
    return normalized[:217].rsplit(" ", 1)[0] + "..."
