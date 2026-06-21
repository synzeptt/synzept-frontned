from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.models.memory import Memory
from app.models.user_understanding import UserUnderstanding
from app.schemas.user_understanding import UserUnderstandingCoverageOut, UserUnderstandingCreate, UserUnderstandingProfileOut, UserUnderstandingUpdate


S1_UNDERSTANDING_CATEGORIES: dict[str, str] = {
    "about_me": "About me",
    "interests": "Interests",
    "habits": "Habits",
    "preferences": "Preferences",
    "company": "Company",
    "job": "Job",
    "projects": "Projects",
    "responsibilities": "Responsibilities",
    "short_term_goals": "Short-term goals",
    "long_term_goals": "Long-term goals",
    "missions": "Mission",
    "important_people": "Important people",
    "commitments": "Commitments",
    "learning_topics": "Learning topics",
    "skills": "Skills",
    "current_focus": "Current focus",
    "current_struggles": "Current struggles",
    "open_loops": "Open loops",
}

MEMORY_TO_UNDERSTANDING_CATEGORY = {
    "identity": "about_me",
    "interests": "interests",
    "routines": "habits",
    "preferences": "preferences",
    "work": "job",
    "projects": "projects",
    "goals": "short_term_goals",
    "long_term_plans": "long_term_goals",
    "skills": "skills",
    "priorities": "current_focus",
    "decisions": "commitments",
}


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
        changes = data.model_dump(exclude_unset=True)
        if item.source == "learned" and any(field in changes for field in ("title", "value")) and "source" not in changes:
            changes["source"] = "user"
            item.confidence = 1.0
        for field, value in changes.items():
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

    async def coverage_for_user(self, user: User) -> UserUnderstandingCoverageOut:
        return self._coverage(await self.list_for_user(user))

    async def sync_from_memories(self, user_id: UUID) -> tuple[int, UserUnderstandingCoverageOut]:
        result = await self.session.execute(
            select(Memory)
            .where(Memory.user_id == user_id, Memory.deleted_at.is_(None))
            .order_by(Memory.importance_score.desc(), Memory.updated_at.desc())
            .limit(200)
        )
        created = await self.learn_from_memories(user_id, list(result.scalars()))
        user = await self.session.get(User, user_id)
        items = await self.list_for_user(user) if user else []
        return created, self._coverage(items)

    async def learn_from_memories(self, user_id: UUID, memories: list[Memory]) -> int:
        if not memories:
            return 0
        result = await self.session.execute(select(UserUnderstanding).where(UserUnderstanding.user_id == user_id))
        existing = list(result.scalars())
        exact = {(item.category, self._normalized(item.value)) for item in existing}
        user_overrides = {(item.category, item.title.casefold()) for item in existing if item.source == "user"}
        created = 0
        now = datetime.now(timezone.utc)
        for memory in memories:
            category = MEMORY_TO_UNDERSTANDING_CATEGORY.get(memory.memory_type or memory.category)
            if not category:
                continue
            value = (memory.summary or memory.content).strip()
            label = S1_UNDERSTANDING_CATEGORIES[category]
            key = (category, self._normalized(value))
            if not value or key in exact or (category, label.casefold()) in user_overrides:
                continue
            self.session.add(
                UserUnderstanding(
                    user_id=user_id,
                    category=category,
                    title=label,
                    value=value[:4000],
                    source="learned",
                    confidence=max(min(memory.confidence or memory.importance_score or 0.65, 1.0), 0.0),
                    learned_at=now,
                )
            )
            exact.add(key)
            created += 1
        if created:
            await self.session.flush()
        return created

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

    @staticmethod
    def _normalized(value: str) -> str:
        return " ".join(value.casefold().split())

    @staticmethod
    def _coverage(items: list[UserUnderstanding]) -> UserUnderstandingCoverageOut:
        completed = sorted({item.category for item in items if item.value.strip() and item.category in S1_UNDERSTANDING_CATEGORIES})
        missing = [category for category in S1_UNDERSTANDING_CATEGORIES if category not in completed]
        learned_dates = [item.learned_at for item in items if item.source == "learned" and item.learned_at]
        total = len(S1_UNDERSTANDING_CATEGORIES)
        return UserUnderstandingCoverageOut(
            completed_categories=completed,
            missing_categories=missing,
            total_categories=total,
            completion_percent=round(len(completed) / total * 100),
            user_items=sum(item.source == "user" for item in items),
            learned_items=sum(item.source == "learned" for item in items),
            last_learned_at=max(learned_dates) if learned_dates else None,
        )
