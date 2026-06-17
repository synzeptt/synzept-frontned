from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.project import Project
from app.models.timeline_event import TimelineEvent
from app.schemas.timeline_phase3 import TimelineEventCreate, TimelineEventUpdate
from app.services.workspace_activity_service import WorkspaceActivityService


class TimelinePhase3Service:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.activity = WorkspaceActivityService(session)

    async def list_events(self, user_id: UUID, project_id: UUID | None = None) -> list[dict]:
        conditions = [TimelineEvent.user_id == user_id]
        if project_id:
            await self._owned_project(user_id, project_id)
            conditions.append(TimelineEvent.project_id == project_id)
        result = await self.session.execute(
            select(TimelineEvent)
            .where(*conditions)
            .order_by(TimelineEvent.event_date.desc(), TimelineEvent.created_at.desc())
        )
        return [self._out(item) for item in result.scalars()]

    async def create_event(self, user_id: UUID, data: TimelineEventCreate) -> dict:
        if data.projectId:
            await self._owned_project(user_id, data.projectId)
        item = TimelineEvent(
            user_id=user_id,
            project_id=data.projectId,
            event_type=data.eventType,
            title=data.title.strip(),
            description=data.description.strip(),
            event_date=data.eventDate,
            importance=data.importance,
        )
        self.session.add(item)
        await self.session.flush()
        await self.activity.record(
            user_id=user_id,
            action=f"timeline_{item.event_type}",
            title=item.title,
            detail=item.description or "",
            project_id=item.project_id,
        )
        return self._out(item)

    async def get_event(self, user_id: UUID, event_id: UUID) -> dict:
        return self._out(await self._owned_event(user_id, event_id))

    async def update_event(self, user_id: UUID, event_id: UUID, data: TimelineEventUpdate) -> dict:
        item = await self._owned_event(user_id, event_id)
        updates = data.model_dump(exclude_unset=True)
        if "projectId" in updates and updates["projectId"] is not None:
            await self._owned_project(user_id, updates["projectId"])
            item.project_id = updates["projectId"]
        if "eventType" in updates and updates["eventType"] is not None:
            item.event_type = updates["eventType"]
        if "title" in updates and updates["title"] is not None:
            item.title = updates["title"].strip()
        if "description" in updates and updates["description"] is not None:
            item.description = updates["description"].strip()
        if "eventDate" in updates and updates["eventDate"] is not None:
            item.event_date = updates["eventDate"]
        if "importance" in updates and updates["importance"] is not None:
            item.importance = updates["importance"]
        item.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.activity.record(
            user_id=user_id,
            action=f"timeline_{item.event_type}_updated",
            title=item.title,
            detail=item.description or "",
            project_id=item.project_id,
        )
        return self._out(item)

    async def delete_event(self, user_id: UUID, event_id: UUID) -> None:
        item = await self._owned_event(user_id, event_id)
        await self.session.delete(item)
        await self.session.flush()

    async def _owned_event(self, user_id: UUID, event_id: UUID) -> TimelineEvent:
        result = await self.session.execute(
            select(TimelineEvent).where(TimelineEvent.id == event_id, TimelineEvent.user_id == user_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("Timeline event not found")
        return item

    async def _owned_project(self, user_id: UUID, project_id: UUID) -> Project:
        result = await self.session.execute(
            select(Project).where(Project.id == project_id, Project.user_id == user_id, Project.deleted_at.is_(None))
        )
        project = result.scalar_one_or_none()
        if not project:
            raise NotFoundError("Project not found")
        return project

    @staticmethod
    def _out(item: TimelineEvent) -> dict:
        return {
            "id": item.id,
            "userId": item.user_id,
            "projectId": item.project_id,
            "eventType": item.event_type,
            "title": item.title,
            "description": item.description or "",
            "eventDate": item.event_date,
            "importance": item.importance,
            "createdAt": item.created_at,
            "updatedAt": item.updated_at,
        }
