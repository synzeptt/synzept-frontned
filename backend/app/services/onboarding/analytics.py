from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import UsageEvent
from app.models.user import User
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
        user = await self.session.get(User, user_id)
        result = await self.session.execute(
            select(func.count(UsageEvent.id)).where(
                UsageEvent.user_id == user_id,
                UsageEvent.surface == "onboarding",
            )
        )
        events_tracked = int(result.scalar() or 0)
        completed_steps = set(onboarding.get("completed_steps", []))
        activation_events = await self._count(
            user_id,
            "first_run_activation_completed",
            "first_run_intelligence_completed",
            "onboarding_completed",
            before=user.created_at + timedelta(days=1) if user else None,
        )
        retention_events = await self._count(
            user_id,
            "daily_active",
            "return_session",
            "dashboard_loaded",
            "daily_brief_viewed",
            after=user.created_at + timedelta(days=7) if user else None,
        )
        daily_brief_opens = await self._count(user_id, "daily_brief_viewed")
        open_loop_completions = await self._count(user_id, "open_loop_completed")

        return OnboardingAnalyticsSummary(
            completed="complete" in completed_steps,
            drop_off_step=None if "complete" in completed_steps else onboarding.get("resume_step"),
            first_ai_interaction_success="first_chat" in completed_steps,
            first_project_created=bool(onboarding.get("first_project_id")),
            first_memory_initialized="memory" in completed_steps,
            day_1_activation=activation_events > 0,
            day_7_retention=retention_events > 0,
            daily_brief_opens=daily_brief_opens,
            open_loop_completions=open_loop_completions,
            events_tracked=events_tracked,
        )

    async def _count(self, user_id: UUID, *event_types: str, before=None, after=None) -> int:
        conditions = [UsageEvent.user_id == user_id, UsageEvent.event_type.in_(event_types)]
        if before is not None:
            conditions.append(UsageEvent.created_at <= before)
        if after is not None:
            conditions.append(UsageEvent.created_at >= after)
        result = await self.session.execute(select(func.count(UsageEvent.id)).where(*conditions))
        return int(result.scalar() or 0)
