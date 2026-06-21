from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.schemas.user_understanding import UserUnderstandingCreate, UserUnderstandingProfileOut, UserUnderstandingUpdate


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

    async def profile_for_user(self, user: User) -> UserUnderstandingProfileOut:
        items = await self.list_for_user(user)
        return UserUnderstandingProfileOut(
            user_id=user.id,
            current_mission=self._values_for(items, titles=("Current Mission", "Mission", "North Star"), categories=("current_mission", "missions", "long_term_goals", "goals")),
            current_focus=self._values_for(items, titles=("Current Focus", "Current Priorities", "Active Projects"), categories=("current_focus", "recent_priorities")),
            active_projects=self._values_for(items, titles=("Active Projects", "Projects"), categories=("projects",)),
            open_loops=self._values_for(items, titles=("Open Loops", "Open Loop", "Unfinished Work"), categories=("open_loops", "commitments")),
            recent_progress=self._values_for(items, titles=("Recent Progress", "Progress", "Wins"), categories=("recent_progress",)),
            recent_decisions=self._values_for(items, titles=("Recent Decisions", "Decision Memory", "Decisions"), categories=("decision_memory",)),
            next_suggested_actions=self._values_for(items, titles=("Next Suggested Actions", "Suggested Next Actions", "Next Actions"), categories=("next_suggested_actions",)),
            updated_at=items[0].updated_at if items else None,
        )

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

    @staticmethod
    def _values_for(items: list[UserUnderstanding], *, titles: tuple[str, ...], categories: tuple[str, ...]) -> list[str]:
        title_keys = {title.casefold() for title in titles}
        category_keys = {category.casefold() for category in categories}
        values: list[str] = []
        for item in items:
            if item.title.casefold() not in title_keys and item.category.casefold() not in category_keys:
                continue
            split = [line.strip(" -*\t") for line in item.value.replace(";", "\n").splitlines() if line.strip(" -*\t")]
            values.extend(split or [item.value.strip()])
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            normalized = value.strip()
            key = normalized.casefold()
            if normalized and key not in seen:
                seen.add(key)
                result.append(normalized)
        return result[:6]
