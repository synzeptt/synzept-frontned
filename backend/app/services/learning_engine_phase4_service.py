from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning import LearningObservation, LearningSuggestion
from app.schemas.learning_engine_phase4 import LearningObservationCreate
from app.services.knows_you_service import KnowsYouService


PATTERNS = {
    "Startup projects": ("startup", "founder", "launch"),
    "AI products": ("ai", "llm", "model", "prompt"),
    "Continuity systems": ("continuity", "memory", "context", "timeline"),
    "Concise communication": ("concise", "brief", "direct"),
}


class LearningEnginePhase4Service:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def overview(self, user_id: UUID) -> dict:
        return {
            "observations": [self._observation_out(item) for item in await self._observations(user_id)],
            "suggestions": await KnowsYouService(self.session).list_suggestions(user_id),
        }

    async def create_observation(self, user_id: UUID, data: LearningObservationCreate) -> dict:
        item = LearningObservation(
            user_id=user_id,
            source=data.source.strip(),
            content=data.content.strip(),
            status="observed",
        )
        self.session.add(item)
        await self.session.flush()
        return self._observation_out(item)

    async def analyze(self, user_id: UUID) -> dict:
        observations = await self._observations(user_id)
        existing_titles = {
            item.title
            for item in (await self.session.execute(select(LearningSuggestion).where(LearningSuggestion.user_id == user_id))).scalars()
        }
        text = [item.content.casefold() for item in observations]
        created = 0
        for title, terms in PATTERNS.items():
            matches = sum(1 for content in text if any(term in content for term in terms))
            if matches < 2 or title in existing_titles:
                continue
            self.session.add(
                LearningSuggestion(
                    user_id=user_id,
                    title=title,
                    description=f"You frequently return to {title.lower()} across observed work.",
                    confidence=min(0.55 + matches * 0.1, 0.95),
                    status="pending",
                )
            )
            created += 1
        now = datetime.now(timezone.utc)
        for item in observations:
            item.status = "analyzed"
            item.updated_at = now
        await self.session.flush()
        return {
            "observationsAnalyzed": len(observations),
            "suggestionsCreated": created,
            "suggestions": await KnowsYouService(self.session).list_suggestions(user_id),
        }

    async def _observations(self, user_id: UUID) -> list[LearningObservation]:
        result = await self.session.execute(
            select(LearningObservation)
            .where(LearningObservation.user_id == user_id)
            .order_by(LearningObservation.created_at.desc())
        )
        return list(result.scalars())

    @staticmethod
    def _observation_out(item: LearningObservation) -> dict:
        return {
            "id": item.id,
            "userId": item.user_id,
            "source": item.source,
            "content": item.content,
            "status": item.status,
            "createdAt": item.created_at,
            "updatedAt": item.updated_at,
        }
