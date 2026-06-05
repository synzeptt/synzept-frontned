from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.timeline_phase3 import TimelineEventCreate, TimelineEventOut, TimelineEventUpdate
from app.services.timeline_phase3_service import TimelinePhase3Service

router = APIRouter(prefix="/api")


@router.get("/timeline-events", response_model=list[TimelineEventOut])
async def list_timeline_events(
    project_id: UUID | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await TimelinePhase3Service(session).list_events(user.id, project_id)


@router.post("/timeline-events", response_model=TimelineEventOut)
async def create_timeline_event(
    body: TimelineEventCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await TimelinePhase3Service(session).create_event(user.id, body)


@router.get("/timeline-events/{event_id}", response_model=TimelineEventOut)
async def get_timeline_event(event_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await TimelinePhase3Service(session).get_event(user.id, event_id)


@router.put("/timeline-events/{event_id}", response_model=TimelineEventOut)
async def update_timeline_event(
    event_id: UUID,
    body: TimelineEventUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await TimelinePhase3Service(session).update_event(user.id, event_id, body)


@router.delete("/timeline-events/{event_id}")
async def delete_timeline_event(event_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    await TimelinePhase3Service(session).delete_event(user.id, event_id)
    return {"ok": True}
