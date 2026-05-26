"""Daily Operating Service — morning briefing, evening summary, dashboard intelligence."""

import json
import logging
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.daily.consolidation import MemoryConsolidation
from app.daily.constants import KIND_EVENING, KIND_MORNING
from app.daily.context import DailyContextService
from app.daily.task_intel import TaskIntelligence
from app.infrastructure.jobs import JobType, enqueue
from app.models.daily_summary import DailySummary
from app.models.user import User
from app.orchestrator.intelligence import IntelligenceOrchestrator
from app.orchestrator.types import ClassifiedIntent, IntentCategory
from app.prompts.daily import EVENING_SUMMARY, MORNING_BRIEFING
from app.services.providers.base import LLMMessage
from app.services.providers.router import LLMRouter
from app.tasks.service import TaskService
from app.utils.text import truncate

logger = logging.getLogger(__name__)


class DailyOperatingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.context = DailyContextService(session)
        self.task_intel = TaskIntelligence(session)
        self.llm = LLMRouter()

    async def get_daily_experience(self, user: User, *, ensure_morning: bool = True) -> dict:
        today = date.today()
        if ensure_morning:
            await self.ensure_morning_briefing(user)

        morning = await self._get(user.id, today, KIND_MORNING)
        evening = await self._get(user.id, today, KIND_EVENING)

        priorities = await TaskService(self.session).get_priorities(user.id)
        suggestions = await self.task_intel.suggestions(user.id)

        focus_areas: list[str] = []
        for t in priorities[:3]:
            focus_areas.append(t.title)
        if not focus_areas and morning and morning.metadata_.get("focus_areas"):
            focus_areas = list(morning.metadata_.get("focus_areas", []))[:3]

        morning_text = morning.summary if morning else (
            self._instant_briefing(priorities) if not ensure_morning else await self._fallback_briefing(user)
        )
        evening_text = evening.summary if evening else None
        rhythm_source = evening or morning
        metadata = rhythm_source.metadata_ if rhythm_source else {}
        tomorrow_priorities = list(metadata.get("tomorrow_priorities", []))[:6]
        continuation_points = list(metadata.get("continuation_points", []))[:6]
        workflow_phase = self._workflow_phase(bool(morning), bool(evening))

        return {
            "date": today.isoformat(),
            "morning_briefing": morning_text,
            "evening_summary": evening_text,
            "briefing": morning_text,
            "workflow_phase": workflow_phase,
            "rhythm_prompt": self._rhythm_prompt(workflow_phase, priorities, continuation_points),
            "focus_areas": focus_areas,
            "suggestions": suggestions,
            "completed_today": list(evening.completed_work if evening else morning.completed_work if morning else []),
            "carry_forward": list(
                evening.unfinished_priorities if evening else morning.unfinished_priorities if morning else []
            ),
            "insights": list(evening.insights if evening else morning.insights if morning else []),
            "tomorrow_priorities": tomorrow_priorities,
            "continuation_points": continuation_points,
            "has_evening": evening is not None,
        }

    async def ensure_morning_briefing(self, user: User) -> DailySummary:
        today = date.today()
        existing = await self._get(user.id, today, KIND_MORNING)
        if existing:
            return existing
        return await self.generate_morning(user)

    async def generate_morning(self, user: User, target_date: date | None = None) -> DailySummary:
        target = target_date or date.today()
        ctx = await self.context.gather_generation_context(user.id, kind=KIND_MORNING)
        text = await self._llm_summary(MORNING_BRIEFING, ctx, user.display_name)
        if not text:
            text = await self._fallback_briefing(user)

        open_tasks = ctx.get("open_tasks", [])
        unfinished = [f"{t['title']} ({t['priority']})" for t in open_tasks[:6]]
        focus = [t["title"] for t in open_tasks[:3]]

        return await self._upsert(
            user.id,
            target,
            KIND_MORNING,
            summary=text,
            unfinished=unfinished,
            completed=[],
            insights=self._extract_insights(text),
            metadata={"focus_areas": focus, "generated_at": datetime.now(timezone.utc).isoformat()},
        )

    async def generate_evening(self, user: User, target_date: date | None = None) -> DailySummary:
        target = target_date or date.today()
        ctx = await self.context.gather_generation_context(user.id, kind=KIND_EVENING)
        text = await self._llm_summary(EVENING_SUMMARY, ctx, user.display_name)
        if not text:
            text = self._fallback_evening(ctx)

        completed = ctx.get("completed_today", [])
        open_tasks = ctx.get("open_tasks", [])
        unfinished = [f"{t['title']}" for t in open_tasks[:6]]

        row = await self._upsert(
            user.id,
            target,
            KIND_EVENING,
            summary=text,
            unfinished=unfinished,
            completed=completed,
            insights=self._extract_insights(text),
            metadata={"generated_at": datetime.now(timezone.utc).isoformat()},
        )
        enqueue(JobType.MEMORY_CONSOLIDATION, user_id=user.id)
        return row

    async def save_wrap_up(
        self,
        user: User,
        *,
        progress_summary: str | None,
        completed: list[str],
        unfinished: list[str],
        insights: list[str],
        tomorrow_priorities: list[str],
        continuation_points: list[str],
    ) -> DailySummary:
        clean_completed = self._clean_items(completed)
        clean_unfinished = self._clean_items(unfinished)
        clean_insights = self._clean_items(insights)
        clean_tomorrow = self._clean_items(tomorrow_priorities)
        clean_continuation = self._clean_items(continuation_points)
        summary = self._manual_wrap_summary(
            progress_summary=progress_summary,
            completed=clean_completed,
            unfinished=clean_unfinished,
            insights=clean_insights,
            tomorrow_priorities=clean_tomorrow,
            continuation_points=clean_continuation,
        )
        row = await self._upsert(
            user.id,
            date.today(),
            KIND_EVENING,
            summary=summary,
            unfinished=clean_unfinished,
            completed=clean_completed,
            insights=clean_insights,
            metadata={
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source": "manual_wrap_up",
                "tomorrow_priorities": clean_tomorrow,
                "continuation_points": clean_continuation,
            },
        )
        enqueue(JobType.MEMORY_CONSOLIDATION, user_id=user.id)
        return row

    async def regenerate(self, user: User, kind: str) -> DailySummary:
        if kind == KIND_EVENING:
            return await self.generate_evening(user)
        return await self.generate_morning(user)

    async def schedule_consolidation(self, user_id: UUID) -> None:
        enqueue(JobType.MEMORY_CONSOLIDATION, user_id=user_id)

    async def _llm_summary(self, system_prompt: str, ctx: dict, display_name: str | None) -> str | None:
        try:
            user_block = json.dumps(ctx, default=str)[:6000]
            messages = [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(
                    role="user",
                    content=f"User: {display_name or 'User'}\n\nData:\n{user_block}",
                ),
            ]
            return await self.llm.complete(messages, temperature=0.25)
        except Exception as exc:
            logger.warning("Daily LLM summary failed: %s", exc)
            return None

    async def _fallback_briefing(self, user: User) -> str:
        brain = IntelligenceOrchestrator(self.session, user.id)
        return await brain._briefing(ClassifiedIntent(category=IntentCategory.BRIEFING))

    @staticmethod
    def _instant_briefing(priorities) -> str:
        if priorities:
            top = priorities[0].title
            return f"Start by continuing: {top}. Keep the day focused on the open work already carrying momentum."
        return "No urgent priority is pulling focus yet. Capture one clear next action to make the workspace easier to resume."

    @staticmethod
    def _workflow_phase(has_morning: bool, has_evening: bool) -> str:
        if has_evening:
            return "closed"
        hour = datetime.now(timezone.utc).astimezone().hour
        if hour >= 17:
            return "wrap_up"
        if has_morning and hour >= 11:
            return "restore"
        return "morning"

    @staticmethod
    def _rhythm_prompt(phase: str, priorities, continuation_points: list[str]) -> str:
        if phase == "closed":
            if continuation_points:
                return f"Tomorrow is preloaded with: {continuation_points[0]}"
            return "Your day is closed. Tomorrow can start from the prepared carry-forward."
        if phase == "wrap_up":
            return "Close the day by preserving what changed, what remains open, and where to resume."
        if phase == "restore":
            if priorities:
                return f"Return gently: pick up {priorities[0].title} or reopen a continuation card."
            return "Restore context from recent conversations, notes, or one active project."
        if priorities:
            return f"Start with {priorities[0].title}, then keep the rest visible but quiet."
        return "Choose one priority to make today easier to resume later."

    @staticmethod
    def _fallback_evening(ctx: dict) -> str:
        lines = ["## Today", ""]
        done = ctx.get("completed_today", [])
        if done:
            lines.extend(f"- {d}" for d in done[:5])
        else:
            lines.append("- Progress was captured in your workspace.")
        lines.append("")
        lines.append("## Still open")
        for t in ctx.get("open_tasks", [])[:5]:
            lines.append(f"- {t['title']}")
        lines.append("")
        lines.append("## Carry forward")
        if ctx.get("open_tasks"):
            lines.append(f"- Start with: {ctx['open_tasks'][0]['title']}")
        else:
            lines.append("- Set tomorrow's focus when ready.")
        return "\n".join(lines)

    @staticmethod
    def _manual_wrap_summary(
        *,
        progress_summary: str | None,
        completed: list[str],
        unfinished: list[str],
        insights: list[str],
        tomorrow_priorities: list[str],
        continuation_points: list[str],
    ) -> str:
        lines = ["## Today"]
        lines.append(progress_summary.strip() if progress_summary and progress_summary.strip() else "Progress was captured in Synzept.")
        if completed:
            lines.extend(["", "## Completed", *[f"- {item}" for item in completed[:8]]])
        if unfinished:
            lines.extend(["", "## Carry forward", *[f"- {item}" for item in unfinished[:8]]])
        if insights:
            lines.extend(["", "## Insights", *[f"- {item}" for item in insights[:6]]])
        if tomorrow_priorities:
            lines.extend(["", "## Tomorrow", *[f"- {item}" for item in tomorrow_priorities[:6]]])
        if continuation_points:
            lines.extend(["", "## Resume from", *[f"- {item}" for item in continuation_points[:6]]])
        return "\n".join(lines)

    @staticmethod
    def _clean_items(items: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in items:
            value = truncate(str(item).strip(), 220)
            if value and value not in cleaned:
                cleaned.append(value)
        return cleaned[:8]

    @staticmethod
    def _extract_insights(text: str) -> list[str]:
        insights: list[str] = []
        if "## Note" in text or "**Note" in text:
            part = text.split("## Note")[-1].split("##")[0].strip()
            if part:
                insights.append(truncate(part, 200))
        return insights[:2]

    async def _get(self, user_id: UUID, day: date, kind: str) -> DailySummary | None:
        result = await self.session.execute(
            select(DailySummary).where(
                DailySummary.user_id == user_id,
                DailySummary.summary_date == day,
                DailySummary.summary_kind == kind,
            )
        )
        return result.scalar_one_or_none()

    async def _upsert(
        self,
        user_id: UUID,
        day: date,
        kind: str,
        *,
        summary: str,
        unfinished: list,
        completed: list,
        insights: list,
        metadata: dict,
    ) -> DailySummary:
        row = await self._get(user_id, day, kind)
        if row:
            row.summary = truncate(summary, 4000)
            row.unfinished_priorities = unfinished
            row.completed_work = completed
            row.insights = insights
            row.metadata_ = metadata
            row.updated_at = datetime.now(timezone.utc)
            return row

        row = DailySummary(
            user_id=user_id,
            summary_date=day,
            summary_kind=kind,
            summary=truncate(summary, 4000),
            unfinished_priorities=unfinished,
            completed_work=completed,
            insights=insights,
            metadata_=metadata,
        )
        self.session.add(row)
        await self.session.flush()
        return row
