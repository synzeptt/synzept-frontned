from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.timeline_event import TimelineEvent
from app.schemas.core import TimelineEventCreate, TimelineEventUpdate


class TimelineService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, user_id: UUID) -> list[TimelineEvent]:
        result = await self.session.execute(select(TimelineEvent).where(TimelineEvent.user_id == user_id).order_by(TimelineEvent.event_date.desc(), TimelineEvent.created_at.desc()))
        return list(result.scalars())

    async def get(self, user_id: UUID, item_id: UUID) -> TimelineEvent:
        result = await self.session.execute(select(TimelineEvent).where(TimelineEvent.id == item_id, TimelineEvent.user_id == user_id))
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("Timeline event not found")
        return item

    async def create(self, user_id: UUID, data: TimelineEventCreate) -> TimelineEvent:
        item = TimelineEvent(user_id=user_id, **data.model_dump())
        self.session.add(item)
        await self.session.flush()
        return item

    async def update(self, user_id: UUID, item_id: UUID, data: TimelineEventUpdate) -> TimelineEvent:
        item = await self.get(user_id, item_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await self.session.flush()
        return item

    async def delete(self, user_id: UUID, item_id: UUID) -> None:
        await self.session.delete(await self.get(user_id, item_id))
