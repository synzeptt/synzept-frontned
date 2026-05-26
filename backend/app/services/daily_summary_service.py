"""Daily summary service — delegates to Daily Operating layer."""

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.daily.constants import KIND_MORNING
from app.daily.operating import DailyOperatingService
from app.models.daily_summary import DailySummary
from app.models.user import User
from app.utils.text import truncate


class DailySummaryService:
    """Backward-compatible facade."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._ops = DailyOperatingService(session)

    async def get_today(self, user_id: UUID) -> DailySummary | None:
        today = date.today()
        result = await self.session.execute(
            select(DailySummary).where(
                DailySummary.user_id == user_id,
                DailySummary.summary_date == today,
                DailySummary.summary_kind == KIND_MORNING,
            )
        )
        return result.scalar_one_or_none()

    async def generate_for_user(self, user_id: UUID, summary_date: str | None = None) -> DailySummary:
        user = await self.session.get(User, user_id)
        if not user:
            raise ValueError("User not found")
        target = date.fromisoformat(summary_date) if summary_date else date.today()
        if target == date.today():
            return await self._ops.generate_morning(user)
        return await self._ops.generate_morning(user, target_date=target)

    async def create_snapshot(
        self,
        user_id: UUID,
        *,
        kind: str,
        summary: str,
        summary_date: date | None = None,
        unfinished: list[str] | None = None,
        completed: list[str] | None = None,
        insights: list[str] | None = None,
        metadata: dict | None = None,
    ) -> DailySummary:
        """Store lightweight continuity, session, or progress summaries."""
        target_date = summary_date or date.today()
        result = await self.session.execute(
            select(DailySummary).where(
                DailySummary.user_id == user_id,
                DailySummary.summary_date == target_date,
                DailySummary.summary_kind == kind,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            row.summary = truncate(summary, 4000)
            row.unfinished_priorities = unfinished or []
            row.completed_work = completed or []
            row.insights = insights or []
            row.metadata_ = metadata or {}
            await self.session.flush()
            return row

        row = DailySummary(
            user_id=user_id,
            summary_date=target_date,
            summary_kind=kind,
            summary=truncate(summary, 4000),
            unfinished_priorities=unfinished or [],
            completed_work=completed or [],
            insights=insights or [],
            metadata_=metadata or {},
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def recent_summaries(self, user_id: UUID, *, kind: str | None = None, limit: int = 10) -> list[DailySummary]:
        query = select(DailySummary).where(DailySummary.user_id == user_id)
        if kind:
            query = query.where(DailySummary.summary_kind == kind)
        result = await self.session.execute(
            query.order_by(DailySummary.summary_date.desc(), DailySummary.updated_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
