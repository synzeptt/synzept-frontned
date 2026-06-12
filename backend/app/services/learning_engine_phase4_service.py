from collections import Counter
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import UsageEvent
from app.models.learning import LearningObservation, LearningSuggestion
from app.models.note import Note
from app.models.project import Project
from app.models.task import Task
from app.models.timeline_event import TimelineEvent
from app.schemas.learning_engine_phase4 import LearningObservationCreate
from app.services.knows_you_service import KnowsYouService
from app.utils.text import truncate


PATTERNS = {
    "You frequently work on startup projects.": {
        "terms": ("startup", "founder", "launch", "mvp", "investor", "saas"),
        "label": "startup-related",
    },
    "You often focus on product development.": {
        "terms": ("product", "feature", "roadmap", "ux", "design", "onboarding", "pricing"),
        "label": "product-development",
    },
    "You prefer concise summaries.": {
        "terms": ("concise", "brief", "short", "direct", "summary", "summarize"),
        "label": "concise-summary",
    },
    "You revisit onboarding-related work regularly.": {
        "terms": ("onboarding", "signup", "activation", "first run", "first session"),
        "label": "onboarding-related",
    },
    "You are building continuity and memory systems.": {
        "terms": ("continuity", "memory", "context", "timeline", "open loop", "daily brief"),
        "label": "continuity-system",
    },
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
        await self._collect_workspace_observations(user_id)
        observations = await self._observations(user_id)
        existing_titles = {
            item.title
            for item in (await self.session.execute(select(LearningSuggestion).where(LearningSuggestion.user_id == user_id))).scalars()
        }
        text = [item.content.casefold() for item in observations]
        created = 0
        for title, pattern in PATTERNS.items():
            terms = pattern["terms"]
            matches = sum(1 for content in text if any(term in content for term in terms))
            if matches < 2 or title in existing_titles:
                continue
            evidence = self._evidence(observations, terms)
            source_explanation = self._source_explanation(evidence, pattern["label"])
            self.session.add(
                LearningSuggestion(
                    user_id=user_id,
                    title=title,
                    description=source_explanation,
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

    async def _collect_workspace_observations(self, user_id: UUID) -> None:
        existing = {
            (item.source, item.content)
            for item in (
                await self.session.execute(select(LearningObservation).where(LearningObservation.user_id == user_id))
            ).scalars()
        }
        sources: list[tuple[str, str]] = []
        projects = (
            await self.session.execute(
                select(Project)
                .where(Project.user_id == user_id, Project.deleted_at.is_(None))
                .order_by(Project.updated_at.desc())
                .limit(60)
            )
        ).scalars()
        notes = (
            await self.session.execute(
                select(Note)
                .where(Note.user_id == user_id, Note.deleted_at.is_(None))
                .order_by(Note.updated_at.desc())
                .limit(80)
            )
        ).scalars()
        tasks = (
            await self.session.execute(
                select(Task)
                .where(Task.user_id == user_id, Task.deleted_at.is_(None))
                .order_by(Task.updated_at.desc())
                .limit(80)
            )
        ).scalars()
        timeline = (
            await self.session.execute(
                select(TimelineEvent)
                .where(TimelineEvent.user_id == user_id)
                .order_by(TimelineEvent.event_date.desc(), TimelineEvent.updated_at.desc())
                .limit(60)
            )
        ).scalars()
        activity = (
            await self.session.execute(
                select(UsageEvent)
                .where(UsageEvent.user_id == user_id)
                .order_by(UsageEvent.created_at.desc())
                .limit(80)
            )
        ).scalars()

        for item in projects:
            sources.append(("project", " ".join(part for part in (item.name, item.description, item.current_focus, item.recommended_next_step, item.context_summary) if part)))
        for item in notes:
            tags = " ".join(str(tag) for tag in (item.tags or []))
            sources.append(("note", " ".join(part for part in (item.title, item.summary, item.content, tags) if part)))
        for item in tasks:
            sources.append(("task", " ".join(part for part in (item.title, item.description, item.status, item.priority) if part)))
        for item in timeline:
            sources.append(("timeline", " ".join(part for part in (item.event_type, item.title, item.description) if part)))
        for item in activity:
            sources.append(("daily_activity", " ".join(part for part in (item.event_type, item.surface) if part)))

        for source, content in sources:
            cleaned = truncate(content.strip(), 1000)
            if not cleaned or (source, cleaned) in existing:
                continue
            self.session.add(LearningObservation(user_id=user_id, source=source, content=cleaned, status="observed"))
            existing.add((source, cleaned))
        await self.session.flush()

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

    @staticmethod
    def _evidence(observations: list[LearningObservation], terms: tuple[str, ...]) -> list[dict]:
        matching = [item for item in observations if any(term in item.content.casefold() for term in terms)]
        return [
            {"source": source.replace("_", " "), "count": count}
            for source, count in Counter(item.source for item in matching).most_common(4)
        ]

    @staticmethod
    def _source_explanation(evidence: list[dict], label: str) -> str:
        if not evidence:
            return f"Based on repeated {label} signals across your Synzept workspace."
        top = evidence[0]
        source = top["source"]
        count = top["count"]
        suffix = "s" if count != 1 else ""
        if len(evidence) == 1:
            return f"Based on {count} {label} signal{suffix} in {source}."
        other_sources = ", ".join(item["source"] for item in evidence[1:3])
        return f"Based on {count} {label} signal{suffix} in {source}, plus related activity in {other_sources}."
