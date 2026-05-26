"""Dashboard aggregation for the daily operating experience."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from dataclasses import asdict
from sqlalchemy.ext.asyncio import AsyncSession

from app.daily.operating import DailyOperatingService
from app.memory.engine import MemoryEngine
from app.models.conversation import Conversation
from app.models.daily_summary import DailySummary
from app.models.feedback import UsageEvent
from app.models.note import Note
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.daily import DailyExperienceOut, DailySuggestion
from app.schemas.dashboard import (
    ContinuityThemeOut,
    ContinuityTimelineOut,
    DashboardOut,
    DashboardStatsOut,
    RecentActivityOut,
    RetentionSignalOut,
    ReturningUserOut,
)
from app.services.continuity import ContinuityRestorationService
from app.services.continuity.intelligence import ContinuityIntelligenceService
from app.services.daily_summary_service import DailySummaryService
from app.tasks.service import OPEN_STATUSES, TaskService
from app.utils.text import truncate


class DashboardAggregationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_dashboard(self, user: User) -> DashboardOut:
        projects = await self._active_projects(user.id)
        conversations = await self._recent_conversations(user.id)
        notes = await self._recent_notes(user.id)

        task_svc = TaskService(self.session)
        tasks = await task_svc.list_tasks(user.id)
        unfinished_tasks = self._unfinished_tasks(tasks)
        priorities = self._rank_priorities(unfinished_tasks)[:6]

        restoration = ContinuityRestorationService(self.session)
        raw_memories = await MemoryEngine(self.session).store.list_for_user(user.id, limit=40)
        memories = restoration.rank_memories_for_dashboard(raw_memories)
        continuity_history = await self._continuity_history(user.id)
        continuity_intelligence = ContinuityIntelligenceService().build_intelligence(
            projects=projects,
            conversations=conversations,
            tasks=tasks,
            notes=notes,
            memories=memories,
            history=continuity_history,
        )
        await DailySummaryService(self.session).create_snapshot(
            user.id,
            kind="continuity",
            summary=continuity_intelligence.continuity_summary,
            unfinished=continuity_intelligence.unresolved_items,
            completed=[],
            insights=continuity_intelligence.memory_evolution,
            metadata=ContinuityIntelligenceService.snapshot_payload(continuity_intelligence),
        )
        daily_raw = await DailyOperatingService(self.session).get_daily_experience(user, ensure_morning=False)
        daily = DailyExperienceOut(**daily_raw)
        continuity_cards = restoration.build_cards(
            projects=projects,
            conversations=conversations,
            tasks=tasks,
            notes=notes,
            memories=memories,
        )
        returning_user = await self._returning_user_experience(
            user.id,
            projects=projects,
            conversations=conversations,
            unfinished_tasks=unfinished_tasks,
            continuity_cards=continuity_cards,
            memories=memories,
        )

        return DashboardOut(
            projects=projects[:8],
            recent_conversations=conversations[:6],
            tasks=tasks[:12],
            unfinished_tasks=unfinished_tasks[:8],
            notes=notes[:8],
            memories=memories,
            continuity_summary=continuity_intelligence.continuity_summary,
            recurring_priorities=[ContinuityThemeOut(**asdict(item)) for item in continuity_intelligence.recurring_priorities],
            ongoing_themes=[ContinuityThemeOut(**asdict(item)) for item in continuity_intelligence.ongoing_themes],
            continuity_timeline=[ContinuityTimelineOut(**asdict(item)) for item in continuity_intelligence.timeline],
            memory_evolution=list(continuity_intelligence.memory_evolution),
            priorities=priorities,
            recent_activity=self._recent_activity(projects, conversations, notes, unfinished_tasks),
            continuity_cards=continuity_cards,
            returning_user=returning_user,
            stats=DashboardStatsOut(
                active_projects=len([project for project in projects if project.status == "active"]),
                open_tasks=len(unfinished_tasks),
                recent_conversations=len(conversations),
                notes_updated=len(notes),
            ),
            briefing=daily.morning_briefing,
            daily=daily,
            morning_briefing=daily.morning_briefing,
            evening_summary=daily.evening_summary,
            focus_areas=daily.focus_areas,
            suggestions=[DailySuggestion(**suggestion) for suggestion in daily_raw.get("suggestions", [])],
        )

    async def _returning_user_experience(
        self,
        user_id,
        *,
        projects: list[Project],
        conversations: list[Conversation],
        unfinished_tasks: list[Task],
        continuity_cards,
        memories,
    ) -> ReturningUserOut:
        last_seen = await self._last_seen_before_today(user_id)
        days_since = None
        if last_seen:
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            days_since = max((datetime.now(timezone.utc) - last_seen).days, 0)

        signals = self._retention_signals(
            projects=projects,
            conversations=conversations,
            unfinished_tasks=unfinished_tasks,
            continuity_cards=continuity_cards,
            memories=memories,
        )
        lead = continuity_cards[0] if continuity_cards else None
        if lead:
            prompt = lead.continuation_prompt or f"Continue {lead.title}?"
            summary = f"{lead.title} is the clearest place to resume."
        elif unfinished_tasks:
            prompt = f"Review {unfinished_tasks[0].title}?"
            summary = "You have unfinished work ready to organize."
        elif projects:
            prompt = f"Open {projects[0].name}?"
            summary = "Your active projects are ready when you return."
        else:
            prompt = "Capture one priority for today?"
            summary = "Start with one priority, project, or note so Synzept has a place to preserve context."

        if days_since and days_since > 0:
            summary = f"Welcome back. {summary}"

        return ReturningUserOut(
            is_returning=last_seen is not None,
            days_since_last_seen=days_since,
            summary=summary,
            prompt=prompt,
            signals=signals[:4],
        )

    async def _last_seen_before_today(self, user_id):
        start_of_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.session.execute(
            select(UsageEvent.created_at)
            .where(
                UsageEvent.user_id == user_id,
                UsageEvent.event_type.in_(("daily_active", "dashboard_loaded", "continuity_card_opened")),
                UsageEvent.created_at < start_of_today,
            )
            .order_by(UsageEvent.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _retention_signals(
        *,
        projects: list[Project],
        conversations: list[Conversation],
        unfinished_tasks: list[Task],
        continuity_cards,
        memories,
    ) -> list[RetentionSignalOut]:
        in_progress = [task for task in unfinished_tasks if task.status == "in_progress"]
        overdue = [task for task in unfinished_tasks if task.due_at and task.due_at < datetime.now(task.due_at.tzinfo or timezone.utc)]
        active_threads = [conversation for conversation in conversations if conversation.active_intent]
        signals: list[RetentionSignalOut] = []
        if continuity_cards:
            signals.append(
                RetentionSignalOut(
                    type="resume",
                    label="Best place to continue",
                    description=continuity_cards[0].title,
                    score=continuity_cards[0].continuity_score,
                    href=continuity_cards[0].href,
                )
            )
        if in_progress:
            signals.append(
                RetentionSignalOut(
                    type="unfinished",
                    label="In-progress work",
                    description=f"{len(in_progress)} active item{'s' if len(in_progress) != 1 else ''} ready to resume.",
                    score=0.86,
                    href="/tasks",
                )
            )
        if overdue:
            signals.append(
                RetentionSignalOut(
                    type="attention",
                    label="Needs attention",
                    description=f"{len(overdue)} overdue item{'s' if len(overdue) != 1 else ''} surfaced without expanding the task list.",
                    score=0.78,
                    href="/tasks",
                )
            )
        if active_threads:
            signals.append(
                RetentionSignalOut(
                    type="thread",
                    label="Open thread",
                    description=active_threads[0].title or active_threads[0].active_intent or "A recent discussion has continuation context.",
                    score=0.74,
                    href=f"/chat?conversation={active_threads[0].id}",
                )
            )
        if projects:
            active_count = len([project for project in projects if project.status == "active"])
            signals.append(
                RetentionSignalOut(
                    type="project",
                    label="Active anchors",
                    description=f"{active_count} project{'s' if active_count != 1 else ''} keeping work organized.",
                    score=0.62,
                    href="/projects",
                )
            )
        if memories:
            signals.append(
                RetentionSignalOut(
                    type="memory",
                    label="Relevant memory",
                    description=truncate(memories[0].summary or memories[0].content, 110),
                    score=0.58,
                    href="/settings",
                )
            )
        signals.sort(key=lambda signal: signal.score, reverse=True)
        return signals

    async def _active_projects(self, user_id) -> list[Project]:
        result = await self.session.execute(
            select(Project)
            .where(
                Project.user_id == user_id,
                Project.deleted_at.is_(None),
                Project.status != "archived",
            )
            .order_by(Project.updated_at.desc())
            .limit(12)
        )
        return list(result.scalars().all())

    async def _recent_conversations(self, user_id) -> list[Conversation]:
        since = datetime.now(timezone.utc) - timedelta(days=14)
        result = await self.session.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
                Conversation.archived_at.is_(None),
                Conversation.updated_at >= since,
            )
            .order_by(Conversation.updated_at.desc())
            .limit(10)
        )
        return list(result.scalars().all())

    async def _recent_notes(self, user_id) -> list[Note]:
        result = await self.session.execute(
            select(Note)
            .where(Note.user_id == user_id, Note.deleted_at.is_(None))
            .order_by(Note.updated_at.desc())
            .limit(10)
        )
        return list(result.scalars().all())

    async def _continuity_history(self, user_id) -> list[DailySummary]:
        today = date.today()
        result = await self.session.execute(
            select(DailySummary)
            .where(
                DailySummary.user_id == user_id,
                DailySummary.summary_kind == "continuity",
                DailySummary.summary_date < today,
            )
            .order_by(DailySummary.summary_date.desc(), DailySummary.updated_at.desc())
            .limit(7)
        )
        return list(result.scalars().all())

    @staticmethod
    def _unfinished_tasks(tasks: list[Task]) -> list[Task]:
        open_tasks = [task for task in tasks if task.status in OPEN_STATUSES]
        open_tasks.sort(key=DashboardAggregationService._task_sort_key, reverse=True)
        return open_tasks

    @staticmethod
    def _rank_priorities(tasks: list[Task]) -> list[Task]:
        ranked = list(tasks)
        ranked.sort(key=DashboardAggregationService._task_sort_key, reverse=True)
        return ranked

    @staticmethod
    def _task_sort_key(task: Task) -> tuple:
        priority_weight = {"high": 30, "medium": 20, "low": 10}.get(task.priority or "low", 10)
        due_weight = 0
        if task.due_at:
            now = datetime.now(task.due_at.tzinfo or timezone.utc)
            days_until_due = (task.due_at - now).days
            due_weight = max(0, 14 - days_until_due)
        status_weight = 5 if task.status == "in_progress" else 0
        return (priority_weight + due_weight + status_weight, task.updated_at)

    @staticmethod
    def _recent_activity(
        projects: list[Project],
        conversations: list[Conversation],
        notes: list[Note],
        tasks: list[Task],
    ) -> list[RecentActivityOut]:
        items: list[RecentActivityOut] = []
        for conversation in conversations[:6]:
            items.append(
                RecentActivityOut(
                    id=conversation.id,
                    type="conversation",
                    title=conversation.title or "Untitled conversation",
                    description=truncate(conversation.summary or conversation.active_intent or "", 120) or None,
                    project_id=conversation.project_id,
                    occurred_at=conversation.updated_at,
                )
            )
        for task in tasks[:8]:
            items.append(
                RecentActivityOut(
                    id=task.id,
                    type="task",
                    title=task.title,
                    description=f"{task.status.replace('_', ' ')} priority: {task.priority}",
                    project_id=task.project_id,
                    occurred_at=task.updated_at,
                )
            )
        for note in notes[:6]:
            items.append(
                RecentActivityOut(
                    id=note.id,
                    type="note",
                    title=note.title or "Untitled note",
                    description=truncate(note.summary or note.content, 120),
                    project_id=note.project_id,
                    occurred_at=note.updated_at,
                )
            )
        for project in projects[:4]:
            items.append(
                RecentActivityOut(
                    id=project.id,
                    type="project",
                    title=project.name,
                    description=truncate(project.context_summary or project.description or "", 120) or None,
                    project_id=project.id,
                    occurred_at=project.updated_at,
                )
            )
        items.sort(key=lambda item: item.occurred_at, reverse=True)
        return items[:10]
