from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_brief_phase8 import DailyBriefSnapshot
from app.services.context_engine_phase6_service import ContextEnginePhase6Service


class DailyBriefPhase8Service:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def today(self, user_id: UUID) -> dict:
        today = date.today()
        result = await self.session.execute(
            select(DailyBriefSnapshot).where(DailyBriefSnapshot.user_id == user_id, DailyBriefSnapshot.brief_date == today)
        )
        brief = result.scalar_one_or_none()
        if brief:
            return self._brief_out(brief)
        return await self.refresh(user_id)

    async def refresh(self, user_id: UUID) -> dict:
        context = await ContextEnginePhase6Service(self.session).refresh(user_id)
        today = date.today()
        result = await self.session.execute(
            select(DailyBriefSnapshot).where(DailyBriefSnapshot.user_id == user_id, DailyBriefSnapshot.brief_date == today)
        )
        brief = result.scalar_one_or_none()
        recent_progress = [
            item for item in context["activeThemes"]
            if item.get("type") in {"timeline_progress", "timeline_achievement", "timeline_milestone"}
        ]
        what_matters = [
            {
                "type": "current_focus",
                "title": context["currentFocus"].get("title", "Current focus"),
                "detail": context["currentFocus"].get("detail", ""),
            },
            *context["activeThemes"][:4],
        ]
        values = {
            "context_snapshot_id": context["id"],
            "what_matters_today": what_matters[:5],
            "open_loops": context["openLoops"][:6],
            "recommended_next_step": context["recommendedNextStep"],
            "recent_progress": recent_progress[:5],
            "context_to_remember": context["importantContext"][:6],
        }
        if brief:
            for field, value in values.items():
                setattr(brief, field, value)
            brief.updated_at = datetime.now(timezone.utc)
        else:
            brief = DailyBriefSnapshot(user_id=user_id, brief_date=today, **values)
            self.session.add(brief)
        await self.session.flush()
        return self._brief_out(brief)

    @staticmethod
    def _brief_out(brief: DailyBriefSnapshot) -> dict:
        now = datetime.now(timezone.utc)
        return {
            "id": brief.id,
            "userId": brief.user_id,
            "contextSnapshotId": brief.context_snapshot_id,
            "briefDate": brief.brief_date,
            "whatMattersToday": brief.what_matters_today or [],
            "openLoops": brief.open_loops or [],
            "recommendedNextStep": brief.recommended_next_step or {},
            "recentProgress": brief.recent_progress or [],
            "contextToRemember": brief.context_to_remember or [],
            "createdAt": brief.created_at or now,
            "updatedAt": brief.updated_at or brief.created_at or now,
        }
