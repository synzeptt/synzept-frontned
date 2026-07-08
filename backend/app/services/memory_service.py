from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.memory import Memory
from app.schemas.core import CoreMemoryCreate, CoreMemoryUpdate


class CoreMemoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, user_id: UUID) -> list[Memory]:
        result = await self.session.execute(
            select(Memory)
            .where(Memory.user_id == user_id, Memory.deleted_at.is_(None), Memory.archived_at.is_(None))
            .order_by(Memory.created_at.desc())
        )
        return list(result.scalars())

    async def get(self, user_id: UUID, item_id: UUID) -> Memory:
        result = await self.session.execute(
            select(Memory).where(Memory.id == item_id, Memory.user_id == user_id, Memory.deleted_at.is_(None), Memory.archived_at.is_(None))
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("Memory not found")
        return item

    async def create(self, user_id: UUID, data: CoreMemoryCreate) -> Memory:
        item = Memory(user_id=user_id, category=data.memory_type, **data.model_dump())
        self.session.add(item)
        await self.session.flush()
        return item

    async def update(self, user_id: UUID, item_id: UUID, data: CoreMemoryUpdate) -> Memory:
        item = await self.get(user_id, item_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        if data.memory_type is not None:
            item.category = data.memory_type
        await self.session.flush()
        return item

    async def delete(self, user_id: UUID, item_id: UUID) -> None:
        item = await self.get(user_id, item_id)
        item.deleted_at = datetime.now(timezone.utc)
