from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.models.learning import LearningSuggestion
from app.models.user_understanding import UserUnderstanding
from app.schemas.knows_you import LearningSuggestionCreate, LearningSuggestionEdit, UserUnderstandingBody

PROFILE_CATEGORY = "profile"
PROFILE_TITLE = "Synzept Knows You"


class KnowsYouService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_understanding(self, user_id: UUID) -> dict:
        profile = await self._profile(user_id)
        return self._profile_out(profile, user_id)

    async def create_understanding(self, user_id: UUID, body: UserUnderstandingBody) -> dict:
        existing = await self._profile(user_id)
        if existing:
            raise AppError(
                "User understanding already exists",
                status_code=409,
                code="understanding_exists",
                user_message="Synzept already has an understanding profile. Update it instead.",
            )
        profile = UserUnderstanding(
            user_id=user_id,
            category=PROFILE_CATEGORY,
            title=PROFILE_TITLE,
            value="",
            source="user",
            personal=body.personal,
            professional=body.professional,
            goals=body.goals,
            preferences=body.preferences,
            learning=body.learning,
            current_focus=body.currentFocus,
        )
        self.session.add(profile)
        await self.session.flush()
        return self._profile_out(profile, user_id)

    async def update_understanding(self, user_id: UUID, body: UserUnderstandingBody) -> dict:
        profile = await self._profile(user_id)
        if not profile:
            return await self.create_understanding(user_id, body)
        profile.updated_at = datetime.now(timezone.utc)
        profile.personal = body.personal
        profile.professional = body.professional
        profile.goals = body.goals
        profile.preferences = body.preferences
        profile.learning = body.learning
        profile.current_focus = body.currentFocus
        await self.session.flush()
        return self._profile_out(profile, user_id)

    async def list_suggestions(self, user_id: UUID) -> list[dict]:
        result = await self.session.execute(
            select(LearningSuggestion)
            .where(LearningSuggestion.user_id == user_id)
            .order_by(LearningSuggestion.created_at.desc())
        )
        return [self._suggestion_out(item) for item in result.scalars()]

    async def create_suggestion(self, user_id: UUID, body: LearningSuggestionCreate) -> dict:
        suggestion = LearningSuggestion(
            user_id=user_id,
            title=body.title.strip(),
            description=body.description.strip(),
            confidence=0.5,
            status="pending",
        )
        self.session.add(suggestion)
        await self.session.flush()
        return self._suggestion_out(suggestion)

    async def edit_suggestion(self, user_id: UUID, suggestion_id: UUID, body: LearningSuggestionEdit) -> dict:
        suggestion = await self._pending_suggestion(user_id, suggestion_id)
        if body.title is not None:
            suggestion.title = body.title.strip()
        if body.description is not None:
            suggestion.description = body.description.strip()
        suggestion.status = "pending"
        suggestion.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return self._suggestion_out(suggestion)

    async def ignore_suggestion(self, user_id: UUID, suggestion_id: UUID) -> dict:
        suggestion = await self._pending_suggestion(user_id, suggestion_id)
        suggestion.status = "ignored"
        suggestion.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return self._suggestion_out(suggestion)

    async def accept_suggestion(self, user_id: UUID, suggestion_id: UUID) -> dict:
        suggestion = await self._pending_suggestion(user_id, suggestion_id)
        profile = await self._profile(user_id)
        if not profile:
            profile = UserUnderstanding(
                user_id=user_id,
                category=PROFILE_CATEGORY,
                title=PROFILE_TITLE,
                value="",
                source="user",
            )
            self.session.add(profile)
            await self.session.flush()

        learning = dict(profile.learning or {})
        existing = learning.get("topicsInterestedIn", "")
        addition = suggestion.description.strip()
        if isinstance(existing, list):
            if addition not in existing:
                existing.append(addition)
            learning["topicsInterestedIn"] = existing
        else:
            lines = [line.strip() for line in str(existing).splitlines() if line.strip()]
            if addition not in lines:
                lines.append(addition)
            learning["topicsInterestedIn"] = "\n".join(lines)
        profile.learning = learning
        suggestion.status = "accepted"
        suggestion.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return self._suggestion_out(suggestion)

    async def _profile(self, user_id: UUID) -> UserUnderstanding | None:
        result = await self.session.execute(
            select(UserUnderstanding).where(
                UserUnderstanding.user_id == user_id,
                UserUnderstanding.category == PROFILE_CATEGORY,
                UserUnderstanding.title == PROFILE_TITLE,
            )
        )
        return result.scalar_one_or_none()

    async def _pending_suggestion(self, user_id: UUID, suggestion_id: UUID) -> LearningSuggestion:
        result = await self.session.execute(
            select(LearningSuggestion).where(
                LearningSuggestion.id == suggestion_id,
                LearningSuggestion.user_id == user_id,
            )
        )
        suggestion = result.scalar_one_or_none()
        if not suggestion:
            raise NotFoundError("Learning suggestion not found")
        if suggestion.status not in {"pending", "edited"}:
            raise AppError(
                "Suggestion already finalized",
                status_code=409,
                code="suggestion_finalized",
                user_message="That suggestion was already accepted or ignored.",
            )
        return suggestion

    @staticmethod
    def _profile_out(profile: UserUnderstanding | None, user_id: UUID) -> dict[str, Any]:
        if not profile:
            now = datetime.now(timezone.utc)
            return {
                "id": UUID(int=0),
                "userId": user_id,
                "personal": {},
                "professional": {},
                "goals": {},
                "preferences": {},
                "learning": {},
                "currentFocus": {},
                "createdAt": now,
                "updatedAt": now,
            }
        return {
            "id": profile.id,
            "userId": profile.user_id,
            "personal": profile.personal or {},
            "professional": profile.professional or {},
            "goals": profile.goals or {},
            "preferences": profile.preferences or {},
            "learning": profile.learning or {},
            "currentFocus": profile.current_focus or {},
            "createdAt": profile.created_at,
            "updatedAt": profile.updated_at,
        }

    @staticmethod
    def _suggestion_out(suggestion: LearningSuggestion) -> dict:
        return {
            "id": suggestion.id,
            "userId": suggestion.user_id,
            "title": suggestion.title,
            "description": suggestion.description,
            "status": "pending" if suggestion.status == "edited" else suggestion.status,
            "createdAt": suggestion.created_at,
            "updatedAt": suggestion.updated_at or suggestion.created_at,
        }
