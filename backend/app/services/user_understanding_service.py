from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.schemas.user_understanding import UserUnderstandingCreate, UserUnderstandingUpdate


class UserUnderstandingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user: User) -> list[UserUnderstanding]:
        result = await self.session.execute(
            select(UserUnderstanding)
            .where(UserUnderstanding.user_id == user.id)
            .order_by(UserUnderstanding.category, UserUnderstanding.created_at, UserUnderstanding.title)
        )
        return list(result.scalars())

    async def create(self, user_id: UUID, data: UserUnderstandingCreate) -> UserUnderstanding:
        item = UserUnderstanding(user_id=user_id, **data.model_dump())
        self.session.add(item)
        await self.session.flush()
        return item

    async def update(self, user_id: UUID, item_id: UUID, data: UserUnderstandingUpdate) -> UserUnderstanding:
        item = await self._get_owned(user_id, item_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await self.session.flush()
        return item

    async def delete(self, user_id: UUID, item_id: UUID) -> None:
        item = await self._get_owned(user_id, item_id)
        await self.session.delete(item)

    async def _get_owned(self, user_id: UUID, item_id: UUID) -> UserUnderstanding:
        result = await self.session.execute(
            select(UserUnderstanding).where(
                UserUnderstanding.id == item_id,
                UserUnderstanding.user_id == user_id,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("Understanding item not found")
        return item
