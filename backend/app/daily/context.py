"""Daily context — rollup for prompts and continuity."""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.daily.constants import KIND_EVENING, KIND_MORNING
from app.models.conversation import Conversation
from app.models.daily_summary import DailySummary
from app.models.project import Project
from app.models.user import User
from app.models.user_profile import UserProfile
from app.tasks.service import TaskService
from app.utils.text import truncate


class DailyContextService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_prompt(self, user_id: UUID) -> str:
        """Compact block injected into chat context."""
        parts: list[str] = []
        today = date.today()

        morning = await self._get_summary(user_id, today, KIND_MORNING)
        if morning:
            parts.append(f"Today's briefing:\n{truncate(morning.summary, 400)}")

        yesterday = today - timedelta(days=1)
        evening = await self._get_summary(user_id, yesterday, KIND_EVENING)
        if evening:
            parts.append(f"Yesterday's close:\n{truncate(evening.summary, 300)}")

        user = await self.session.get(User, user_id)
        if user and user.profile_summary:
            parts.append(f"Profile: {truncate(user.profile_summary, 200)}")

        priorities = await TaskService(self.session).get_priorities(user_id, limit=4)
        if priorities:
            parts.append("Open priorities: " + "; ".join(t.title for t in priorities))

        return "\n\n".join(parts) if parts else ""

    async def gather_generation_context(self, user_id: UUID, *, kind: str) -> dict:
        """Raw facts for LLM morning/evening generation."""
        user = await self.session.get(User, user_id)
        profile = await self.session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        prof = profile.scalar_one_or_none()

        tasks = await TaskService(self.session).list_tasks(user_id)
        open_tasks = [t for t in tasks if t.status != "done"]
        done_today = [
            t for t in tasks
            if t.status == "done" and t.updated_at and t.updated_at.date() == date.today()
        ]

        projects = list(
            (
                await self.session.execute(
                    select(Project).where(
                        Project.user_id == user_id,
                        Project.deleted_at.is_(None),
                        Project.status == "active",
                    ).limit(6)
                )
            )
            .scalars()
            .all()
        )

        convs = list(
            (
                await self.session.execute(
                    select(Conversation)
                    .where(
                        Conversation.user_id == user_id,
                        Conversation.deleted_at.is_(None),
                        Conversation.updated_at >= datetime.now(timezone.utc) - timedelta(days=2),
                    )
                    .order_by(Conversation.updated_at.desc())
                    .limit(5)
                )
            )
            .scalars()
            .all()
        )

        from app.memory.engine import MemoryEngine

        memories = await MemoryEngine(self.session).store.list_for_user(user_id, limit=8)

        return {
            "kind": kind,
            "display_name": user.display_name if user else None,
            "goals": list(prof.goals or [])[:5] if prof else [],
            "open_tasks": [{"title": t.title, "priority": t.priority} for t in open_tasks[:8]],
            "completed_today": [t.title for t in done_today[:8]],
            "projects": [{"name": p.name, "summary": truncate(p.context_summary or "", 120)} for p in projects],
            "conversation_summaries": [truncate(c.summary, 150) for c in convs if c.summary],
            "memories": [truncate(m.content, 120) for m in memories[:6]],
        }

    async def _get_summary(self, user_id: UUID, day: date, kind: str) -> DailySummary | None:
        result = await self.session.execute(
            select(DailySummary).where(
                DailySummary.user_id == user_id,
                DailySummary.summary_date == day,
                DailySummary.summary_kind == kind,
            )
        )
        return result.scalar_one_or_none()
