from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.services.knows_you_service import PROFILE_CATEGORY, PROFILE_TITLE, KnowsYouService
from app.services.understanding_extraction_service import UnderstandingFact
from app.services.user_understanding_service import UserUnderstandingService


@dataclass(slots=True)
class UnderstandingUpdateResult:
    created: int = 0
    updated: int = 0
    unchanged: int = 0


class UnderstandingUpdateService:
    """Maintains the durable structured understanding rows and Knows You JSON profile."""

    SINGLETON_CATEGORIES = {"current_focus", "priorities", "next_suggested_actions"}
    SECTION_COLUMNS = {
        "identity": "personal",
        "personal_life": "personal",
        "professional_life": "professional",
        "goals": "goals",
        "relationships": "learning",
        "current_state": "current_focus",
        "intelligence": "learning",
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def apply_facts(self, user_id: UUID, facts: list[UnderstandingFact]) -> UnderstandingUpdateResult:
        result = UnderstandingUpdateResult()
        for fact in facts:
            changed = await self._upsert_fact(user_id, fact)
            if changed == "created":
                result.created += 1
            elif changed == "updated":
                result.updated += 1
            else:
                result.unchanged += 1
        await self._sync_profile_json(user_id, facts)
        return result

    async def coverage(self, user: User):
        return await UserUnderstandingService(self.session).coverage_for_user(user)

    async def _upsert_fact(self, user_id: UUID, fact: UnderstandingFact) -> str:
        result = await self.session.execute(
            select(UserUnderstanding).where(
                UserUnderstanding.user_id == user_id,
                UserUnderstanding.category == fact.category,
                UserUnderstanding.title == fact.title,
            )
        )
        candidates = list(result.scalars())
        exact = next((item for item in candidates if self._normalize(item.value) == self._normalize(fact.value)), None)
        if exact:
            if exact.source == "learned":
                exact.confidence = max(exact.confidence or 0.0, fact.confidence)
            return "unchanged"

        learned = next((item for item in candidates if item.source == "learned"), None)
        if learned and fact.confidence >= (learned.confidence or 0.0):
            if fact.category in self.SINGLETON_CATEGORIES:
                learned.value = fact.value[:4000]
                learned.confidence = fact.confidence
                learned.learned_at = datetime.now(timezone.utc)
                learned.updated_at = datetime.now(timezone.utc)
                await self.session.flush()
                return "updated"

        self.session.add(
            UserUnderstanding(
                user_id=user_id,
                category=fact.category,
                title=fact.title,
                value=fact.value[:4000],
                source="learned",
                confidence=fact.confidence,
                learned_at=datetime.now(timezone.utc),
            )
        )
        await self.session.flush()
        return "created"

    async def _sync_profile_json(self, user_id: UUID, facts: list[UnderstandingFact]) -> None:
        if not facts:
            return
        profile = await KnowsYouService(self.session)._profile(user_id)
        if not profile:
            profile = UserUnderstanding(user_id=user_id, category=PROFILE_CATEGORY, title=PROFILE_TITLE, value="", source="learned")
            self.session.add(profile)
            await self.session.flush()

        for fact in facts:
            column = self.SECTION_COLUMNS.get(fact.section)
            if not column:
                continue
            payload = dict(getattr(profile, column) or {})
            payload = self._append_field(payload, fact.field, fact.value)
            setattr(profile, column, payload)
        profile.updated_at = datetime.now(timezone.utc)
        await self.session.flush()

    @staticmethod
    def _append_field(payload: dict, field: str, value: str) -> dict:
        existing = payload.get(field)
        if existing is None or existing == "":
            payload[field] = value
            return payload
        if isinstance(existing, list):
            if value not in existing:
                existing.append(value)
            payload[field] = existing[:8]
            return payload
        lines = [line.strip() for line in str(existing).replace(";", "\n").splitlines() if line.strip()]
        if value not in lines:
            lines.append(value)
        payload[field] = "\n".join(lines[:8])
        return payload

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.casefold().split())
