from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.goal import Goal
from app.schemas.core import CoreGoalCreate, CoreGoalUpdate


class GoalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, user_id: UUID) -> list[Goal]:
        result = await self.session.execute(select(Goal).where(Goal.user_id == user_id, Goal.deleted_at.is_(None)).order_by(Goal.created_at.desc()))
        return list(result.scalars())

    async def get(self, user_id: UUID, item_id: UUID) -> Goal:
        result = await self.session.execute(select(Goal).where(Goal.id == item_id, Goal.user_id == user_id, Goal.deleted_at.is_(None)))
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("Goal not found")
        return item

    async def create(self, user_id: UUID, data: CoreGoalCreate) -> Goal:
        item = Goal(user_id=user_id, **data.model_dump())
        self.session.add(item)
        await self.session.flush()
        return item

    async def update(self, user_id: UUID, item_id: UUID, data: CoreGoalUpdate) -> Goal:
        item = await self.get(user_id, item_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await self.session.flush()
        return item

    async def delete(self, user_id: UUID, item_id: UUID) -> None:
        item = await self.get(user_id, item_id)
        item.deleted_at = datetime.now(timezone.utc)
