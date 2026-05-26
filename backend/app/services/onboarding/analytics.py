from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import UsageEvent
from app.schemas.onboarding import OnboardingAnalyticsSummary


class OnboardingAnalytics:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def track(
        self,
        *,
        user_id: UUID,
        event_type: str,
        step: str,
        metadata: dict | None = None,
        value: int | None = None,
    ) -> None:
        self.session.add(
            UsageEvent(
                user_id=user_id,
                event_type=event_type,
                surface="onboarding",
                value=value,
                metadata_={"step": step, **(metadata or {})},
            )
        )
        await self.session.flush()

    async def summary(self, user_id: UUID, preferences: dict | None) -> OnboardingAnalyticsSummary:
        onboarding = (preferences or {}).get("onboarding", {})
        result = await self.session.execute(
            select(func.count(UsageEvent.id)).where(
                UsageEvent.user_id == user_id,
                UsageEvent.surface == "onboarding",
            )
        )
        events_tracked = int(result.scalar() or 0)
        completed_steps = set(onboarding.get("completed_steps", []))

        return OnboardingAnalyticsSummary(
            completed="complete" in completed_steps,
            drop_off_step=None if "complete" in completed_steps else onboarding.get("resume_step"),
            first_ai_interaction_success="first_chat" in completed_steps,
            first_project_created=bool(onboarding.get("first_project_id")),
            first_memory_initialized="memory" in completed_steps,
            events_tracked=events_tracked,
        )
