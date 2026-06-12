from collections import Counter
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.models.conversation import Conversation
from app.models.daily_brief import DailyBrief
from app.models.feedback import UsageEvent
from app.models.learning import LearningObservation, LearningSuggestion
from app.models.project import Project
from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.schemas.learning import LearningSettingsUpdate, LearningSuggestionUpdate


PATTERNS = {
    "Startup Building": ("startup", "founder", "launch", "acquisition"),
    "AI Products": ("ai", "artificial intelligence", "llm", "model", "prompt"),
    "Continuity Systems": ("continuity", "memory", "timeline", "context"),
    "Product Design": ("design", "ux", "interface", "onboarding"),
    "Prefers Concise Responses": ("concise", "brief response", "short answer", "direct response"),
}


class LearningEngineService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_engine(self, user: User) -> dict:
        observations = await self._observations(user.id)
        suggestions = await self._suggestions(user.id)
        approved = await self._approved(user.id)
        return {
            "observations": observations,
            "suggestions": [self._suggestion_with_evidence(item, observations) for item in suggestions],
            "approved_understanding": approved,
            "settings": self._settings(user),
        }

    async def analyze(self, user: User) -> dict:
        settings = self._settings(user)
        if not settings["enabled"] or settings["paused"]:
            raise AppError(
                "Learning is disabled or paused",
                status_code=409,
                code="learning_inactive",
                user_message="Enable learning and remove the pause before analyzing activity.",
            )
        await self._collect_observations(user.id)
        await self._detect_patterns(user.id)
        return await self.get_engine(user)

    async def update_settings(self, user: User, data: LearningSettingsUpdate) -> dict:
        preferences = dict(user.preferences or {})
        if data.enabled is not None:
            preferences["learning_enabled"] = data.enabled
        if data.paused is not None:
            preferences["learning_paused"] = data.paused
        user.preferences = preferences
        return self._settings(user)

    async def clear_history(self, user_id: UUID) -> None:
        await self.session.execute(delete(LearningObservation).where(LearningObservation.user_id == user_id))
        await self.session.execute(delete(LearningSuggestion).where(LearningSuggestion.user_id == user_id))

    async def edit_suggestion(
        self,
        user_id: UUID,
        suggestion_id: UUID,
        data: LearningSuggestionUpdate,
    ) -> LearningSuggestion:
        suggestion = await self._owned_suggestion(user_id, suggestion_id)
        if suggestion.status not in {"pending", "edited"}:
            raise AppError("Suggestion is no longer editable", status_code=409, code="suggestion_finalized")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(suggestion, field, value.strip())
        suggestion.status = "edited"
        await self.session.flush()
        return suggestion

    async def ignore_suggestion(self, user_id: UUID, suggestion_id: UUID) -> LearningSuggestion:
        suggestion = await self._owned_suggestion(user_id, suggestion_id)
        if suggestion.status not in {"pending", "edited"}:
            raise AppError("Suggestion is already finalized", status_code=409, code="suggestion_finalized")
        suggestion.status = "ignored"
        await self.session.flush()
        return suggestion

    async def accept_suggestion(self, user_id: UUID, suggestion_id: UUID) -> UserUnderstanding:
        suggestion = await self._owned_suggestion(user_id, suggestion_id)
        if suggestion.status not in {"pending", "edited"}:
            raise AppError("Suggestion is already finalized", status_code=409, code="suggestion_finalized")
        understanding = UserUnderstanding(
            user_id=user_id,
            category="learned_insights",
            title=suggestion.title,
            value=suggestion.description,
            source="learned",
            confidence=suggestion.confidence,
            learned_at=datetime.now(timezone.utc),
        )
        self.session.add(understanding)
        suggestion.status = "accepted"
        await self.session.flush()
        return understanding

    async def _collect_observations(self, user_id: UUID) -> None:
        sources: list[tuple[str, str]] = []
        conversations = list(
            (await self.session.execute(select(Conversation).where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None)))).scalars()
        )
        projects = list(
            (await self.session.execute(select(Project).where(Project.user_id == user_id, Project.deleted_at.is_(None)))).scalars()
        )
        briefs = list((await self.session.execute(select(DailyBrief).where(DailyBrief.user_id == user_id))).scalars())
        understanding = list(
            (await self.session.execute(select(UserUnderstanding).where(UserUnderstanding.user_id == user_id, UserUnderstanding.source == "user"))).scalars()
        )
        events = list(
            (await self.session.execute(select(UsageEvent).where(UsageEvent.user_id == user_id).order_by(UsageEvent.created_at.desc()).limit(40))).scalars()
        )
        sources.extend(("conversation", " ".join(part for part in (item.title, item.summary, item.active_intent) if part)) for item in conversations)
        sources.extend(("project", " ".join(part for part in (item.name, item.description, item.context_summary) if part)) for item in projects)
        sources.extend(
            ("goal" if item.category == "goals" else "user_understanding", item.value)
            for item in understanding
        )
        sources.extend(("daily_brief", " ".join([item.summary, item.next_step, *item.open_loops])) for item in briefs)
        sources.extend(("workspace_activity", " ".join(part for part in (item.event_type, item.surface) if part)) for item in events)
        existing = {
            tuple(row)
            for row in (
                await self.session.execute(
                    select(
                        LearningObservation.user_id,
                        LearningObservation.source,
                        LearningObservation.content,
                    ).where(LearningObservation.user_id == user_id)
                )
            ).all()
        }
        for source, signal in sources:
            cleaned = signal.strip()
            key = (user_id, source, cleaned)
            if cleaned and key not in existing:
                self.session.add(LearningObservation(user_id=user_id, source=source, content=cleaned))
        await self.session.flush()

    async def _detect_patterns(self, user_id: UUID) -> None:
        observations = await self._observations(user_id)
        text = [item.content.casefold() for item in observations]
        pending = {
            item.title
            for item in await self._suggestions(user_id)
            if item.status in {"pending", "edited", "accepted", "ignored"}
        }
        for title, terms in PATTERNS.items():
            matches = sum(1 for signal in text if any(term in signal for term in terms))
            if matches < 2 or title in pending:
                continue
            confidence = min(0.55 + matches * 0.08, 0.96)
            self.session.add(
                LearningSuggestion(
                    user_id=user_id,
                    title=title,
                    description=f"You frequently return to {title.lower()} across your Synzept activity.",
                    confidence=confidence,
                    status="pending",
                )
            )
        await self.session.flush()

    async def _owned_suggestion(self, user_id: UUID, suggestion_id: UUID) -> LearningSuggestion:
        result = await self.session.execute(
            select(LearningSuggestion).where(LearningSuggestion.id == suggestion_id, LearningSuggestion.user_id == user_id)
        )
        suggestion = result.scalar_one_or_none()
        if not suggestion:
            raise NotFoundError("Learning suggestion not found")
        return suggestion

    async def _observations(self, user_id: UUID) -> list[LearningObservation]:
        result = await self.session.execute(
            select(LearningObservation).where(LearningObservation.user_id == user_id).order_by(LearningObservation.created_at.desc()).limit(80)
        )
        return list(result.scalars())

    async def _suggestions(self, user_id: UUID) -> list[LearningSuggestion]:
        result = await self.session.execute(
            select(LearningSuggestion).where(LearningSuggestion.user_id == user_id).order_by(LearningSuggestion.created_at.desc())
        )
        return list(result.scalars())

    async def _approved(self, user_id: UUID) -> list[UserUnderstanding]:
        result = await self.session.execute(
            select(UserUnderstanding)
            .where(UserUnderstanding.user_id == user_id, UserUnderstanding.source == "learned")
            .order_by(UserUnderstanding.learned_at.desc(), UserUnderstanding.created_at.desc())
        )
        return list(result.scalars())

    @staticmethod
    def _settings(user: User) -> dict:
        preferences = user.preferences or {}
        return {
            "enabled": preferences.get("learning_enabled", True),
            "paused": preferences.get("learning_paused", False),
        }

    @staticmethod
    def _suggestion_with_evidence(suggestion: LearningSuggestion, observations: list[LearningObservation]) -> dict:
        terms = PATTERNS.get(suggestion.title, ())
        matches = [item for item in observations if any(term in item.content.casefold() for term in terms)]
        return {
            "id": suggestion.id,
            "user_id": suggestion.user_id,
            "title": suggestion.title,
            "description": suggestion.description,
            "confidence": suggestion.confidence,
            "status": suggestion.status,
            "created_at": suggestion.created_at,
            "evidence": [
                {"source": source.replace("_", " "), "count": count}
                for source, count in Counter(item.source for item in matches).most_common(4)
            ],
        }
