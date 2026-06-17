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
from app.models.project_intelligence_phase2 import Decision
from app.models.task import Task
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.schemas.daily import DailyExperienceOut, DailySuggestion
from app.schemas.dashboard import (
    ContinuityThemeOut,
    ContinuityTimelineOut,
    DashboardOut,
    DashboardStatsOut,
    PersonalOSOut,
    RecentActivityOut,
    ReturnActivityCountsOut,
    ReturnChangeOut,
    ReturnContextOut,
    ReturnOpenLoopOut,
    ReturnRecommendationOut,
    RetentionSignalOut,
    ReturningUserOut,
)
from app.services.continuity import ContinuityRestorationService
from app.services.continuity.intelligence import ContinuityIntelligenceService
from app.services.daily_summary_service import DailySummaryService
from app.services.open_loops_engine_service import OpenLoopsEngineService
from app.services.relationship_graph_phase5_service import RelationshipGraphPhase5Service
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
        recent_activity = self._recent_activity(projects, conversations, notes, tasks)
        returning_user = await self._returning_user_experience(
            user.id,
            projects=projects,
            conversations=conversations,
            notes=notes,
            tasks=tasks,
            unfinished_tasks=unfinished_tasks,
            continuity_cards=continuity_cards,
            memories=memories,
            recent_activity=recent_activity,
        )
        personal_os = await self._personal_os(
            user,
            projects=projects,
            conversations=conversations,
            notes=notes,
            tasks=tasks,
            unfinished_tasks=unfinished_tasks,
            priorities=priorities,
            recent_activity=recent_activity,
            continuity_cards=continuity_cards,
            returning_user=returning_user,
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
            recent_activity=recent_activity,
            continuity_cards=continuity_cards,
            returning_user=returning_user,
            personal_os=personal_os,
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

    async def _personal_os(
        self,
        user: User,
        *,
        projects: list[Project],
        conversations: list[Conversation],
        notes: list[Note],
        tasks: list[Task],
        unfinished_tasks: list[Task],
        priorities: list[Task],
        recent_activity: list[RecentActivityOut],
        continuity_cards,
        returning_user: ReturningUserOut,
    ) -> PersonalOSOut:
        understanding = await self._understanding(user.id)
        open_loop_engine = await OpenLoopsEngineService(self.session).list(user.id)
        decisions = await self._return_decisions(user.id)
        active_projects = [project for project in projects if project.status == "active"]
        current_mission = self._understanding_first(
            understanding,
            titles=("Current Mission", "Mission", "North Star", "Long-Term Goals", "Short-Term Goals"),
            categories=("current_mission", "goals"),
        ) or self._mission_from_projects(active_projects, unfinished_tasks)
        current_focus = self._understanding_first(
            understanding,
            titles=("Current Focus", "Current Priorities", "Active Projects"),
            categories=("current_focus", "recent_priorities"),
        ) or self._focus_from_workspace(active_projects, priorities, continuity_cards)

        loop_rows = [
            ReturnOpenLoopOut(
                id=item.id,
                title=item.title,
                description=item.description,
                project_id=item.projectId,
                project_name=item.projectName,
                type=item.type,
                priority=item.priority,
                href=item.href,
                next_step=item.nextStep,
            )
            for item in open_loop_engine.items[:6]
        ]
        suggested = returning_user.recommended_next_step or self._return_recommendation(
            open_loops=loop_rows,
            continuity_cards=continuity_cards,
            unfinished_tasks=unfinished_tasks,
            projects=projects,
        )
        recent_decisions = [
            ReturnContextOut(
                title=decision.title,
                detail=decision.outcome or decision.reason or decision.description or "Decision recorded.",
                type="decision",
                href=f"/projects/{decision.project_id}",
            )
            for decision in decisions
            if decision.status == "decided"
        ][:5]
        risks = [
            ReturnContextOut(
                title=loop.title,
                detail=loop.description or loop.next_step,
                type=loop.type,
                href=loop.href,
            )
            for loop in loop_rows
            if loop.priority == "high" or loop.type in {"blocked_work", "pending_decision"}
        ][:4]

        return PersonalOSOut(
            greeting=f"Good morning, {user.display_name or 'there'}",
            current_mission=current_mission,
            current_focus=current_focus,
            top_priorities=[
                ReturnContextOut(
                    title=task.title,
                    detail=task.description or task.priority or "Priority task",
                    type="task",
                    href="/tasks",
                )
                for task in priorities[:5]
            ],
            open_loops=loop_rows,
            recent_progress=recent_activity[:6],
            active_projects=[
                ReturnContextOut(
                    title=project.name,
                    detail=project.current_focus or project.recommended_next_step or project.description or "Active project.",
                    type="project",
                    href=f"/projects/{project.id}",
                )
                for project in active_projects[:6]
            ],
            recent_decisions=recent_decisions,
            suggested_next_action=suggested,
            daily_focus=suggested.title,
            risks=risks,
        )

    async def _understanding(self, user_id) -> list[UserUnderstanding]:
        result = await self.session.execute(
            select(UserUnderstanding)
            .where(UserUnderstanding.user_id == user_id)
            .order_by(UserUnderstanding.updated_at.desc())
            .limit(80)
        )
        return list(result.scalars().all())

    async def _returning_user_experience(
        self,
        user_id,
        *,
        projects: list[Project],
        conversations: list[Conversation],
        notes: list[Note],
        tasks: list[Task],
        unfinished_tasks: list[Task],
        continuity_cards,
        memories,
        recent_activity: list[RecentActivityOut],
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

        activity_counts = ReturnActivityCountsOut()
        what_changed: list[ReturnChangeOut] = []
        return_open_loops: list[ReturnOpenLoopOut] = []
        recommended_next_step: ReturnRecommendationOut | None = None
        context_to_remember: list[ReturnContextOut] = []

        if last_seen:
            project_names = {project.id: project.name for project in projects}
            open_loop_engine = await OpenLoopsEngineService(self.session).list(user_id)
            decisions = await self._return_decisions(user_id)
            timeline_events = await self._return_timeline_events(user_id)

            updated_projects = [project for project in projects if self._after(project.updated_at, last_seen)]
            completed_tasks = [
                task
                for task in tasks
                if task.status in {"completed", "done"} and self._after(getattr(task, "updated_at", task.created_at), last_seen)
            ]
            recent_open_loops = [item for item in open_loop_engine.items if self._after(item.createdAt, last_seen)]
            decided = [decision for decision in decisions if decision.status == "decided" and self._after(decision.updated_at, last_seen)]
            milestones = [
                event
                for event in timeline_events
                if event.event_type in {"milestone", "achievement"} and event.event_date >= last_seen.date()
            ]
            activity_counts = ReturnActivityCountsOut(
                projects_updated=len(updated_projects),
                tasks_completed=len(completed_tasks),
                open_loops_created=len(recent_open_loops),
                decisions_made=len(decided),
                milestones_reached=len(milestones),
            )
            what_changed = self._return_changes(
                recent_activity=recent_activity,
                timeline_events=timeline_events,
                project_names=project_names,
                since=last_seen,
            )
            return_open_loops = [
                ReturnOpenLoopOut(
                    id=item.id,
                    title=item.title,
                    description=item.description,
                    project_id=item.projectId,
                    project_name=item.projectName,
                    type=item.type,
                    priority=item.priority,
                    href=item.href,
                    next_step=item.nextStep,
                )
                for item in open_loop_engine.items[:5]
            ]
            recommended_next_step = self._return_recommendation(
                open_loops=return_open_loops,
                continuity_cards=continuity_cards,
                unfinished_tasks=unfinished_tasks,
                projects=projects,
            )
            context_to_remember = self._return_context(
                decisions=decisions,
                open_loops=return_open_loops,
                notes=notes,
                project_names=project_names,
            )
            graph_insights = await RelationshipGraphPhase5Service(self.session).insights(user_id)
            context_to_remember.extend(
                ReturnContextOut(
                    title=item.get("title", "Related context"),
                    detail=item.get("detail", "This relationship may matter as you resume."),
                    type=item.get("type", "relationship"),
                    href="/relationship-graph",
                )
                for item in graph_insights[:3]
            )
            context_to_remember = context_to_remember[:6]

        return ReturningUserOut(
            is_returning=last_seen is not None,
            days_since_last_seen=days_since,
            last_seen_at=last_seen,
            summary=summary,
            prompt=prompt,
            signals=signals[:4],
            activity_counts=activity_counts,
            what_changed=what_changed,
            open_loops=return_open_loops,
            recommended_next_step=recommended_next_step,
            context_to_remember=context_to_remember,
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

    async def _return_decisions(self, user_id) -> list[Decision]:
        result = await self.session.execute(
            select(Decision)
            .join(Project, Project.id == Decision.project_id)
            .where(Project.user_id == user_id, Project.deleted_at.is_(None))
            .order_by(Decision.updated_at.desc())
            .limit(80)
        )
        return list(result.scalars().all())

    async def _return_timeline_events(self, user_id) -> list[TimelineEvent]:
        result = await self.session.execute(
            select(TimelineEvent)
            .where(TimelineEvent.user_id == user_id)
            .order_by(TimelineEvent.event_date.desc(), TimelineEvent.updated_at.desc())
            .limit(80)
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

    @staticmethod
    def _return_changes(
        *,
        recent_activity: list[RecentActivityOut],
        timeline_events: list[TimelineEvent],
        project_names: dict,
        since: datetime,
    ) -> list[ReturnChangeOut]:
        changes: list[ReturnChangeOut] = []
        for item in recent_activity:
            if not DashboardAggregationService._after(item.occurred_at, since):
                continue
            changes.append(
                ReturnChangeOut(
                    id=str(item.id),
                    type=item.type,
                    title=item.title,
                    description=item.description,
                    project_id=item.project_id,
                    project_name=project_names.get(item.project_id, "Workspace"),
                    occurred_at=item.occurred_at,
                    href=DashboardAggregationService._activity_href(item),
                )
            )
        for event in timeline_events:
            if event.event_date < since.date():
                continue
            changes.append(
                ReturnChangeOut(
                    id=str(event.id),
                    type=event.event_type,
                    title=event.title,
                    description=truncate(event.description or "", 120) or None,
                    project_id=event.project_id,
                    project_name=project_names.get(event.project_id, "Workspace"),
                    occurred_at=event.updated_at,
                    href=f"/projects/{event.project_id}" if event.project_id else "/dashboard",
                )
            )
        changes.sort(key=lambda item: DashboardAggregationService._sort_timestamp(item.occurred_at or since), reverse=True)
        return changes[:8]

    @staticmethod
    def _return_recommendation(
        *,
        open_loops: list[ReturnOpenLoopOut],
        continuity_cards,
        unfinished_tasks: list[Task],
        projects: list[Project],
    ) -> ReturnRecommendationOut:
        high_loop = next((item for item in open_loops if item.priority == "high"), None)
        if high_loop:
            return ReturnRecommendationOut(
                title=high_loop.next_step or high_loop.title,
                reason=f"{high_loop.project_name} has unfinished work that still needs attention.",
                href=high_loop.href,
            )
        if continuity_cards:
            card = continuity_cards[0]
            return ReturnRecommendationOut(
                title=card.continuation_prompt or card.title,
                reason=card.reason or card.description,
                href=card.href,
            )
        if unfinished_tasks:
            task = unfinished_tasks[0]
            return ReturnRecommendationOut(
                title=task.title,
                reason="This is the clearest unfinished task to resume.",
                href="/tasks",
            )
        if projects:
            project = projects[0]
            return ReturnRecommendationOut(
                title=project.recommended_next_step or project.current_focus or project.name,
                reason=f"{project.name} is the most recently active project.",
                href=f"/projects/{project.id}",
            )
        return ReturnRecommendationOut(
            title="Capture one priority for today.",
            reason="Synzept needs one active project, task, or note to preserve continuity.",
            href="/projects",
        )

    @staticmethod
    def _understanding_first(
        items: list[UserUnderstanding],
        *,
        titles: tuple[str, ...],
        categories: tuple[str, ...],
    ) -> str:
        title_keys = {title.casefold() for title in titles}
        category_keys = {category.casefold() for category in categories}
        for item in items:
            if item.title.casefold() in title_keys or item.category.casefold() in category_keys:
                values = DashboardAggregationService._split_lines(item.value)
                if values:
                    return values[0]
        return ""

    @staticmethod
    def _mission_from_projects(projects: list[Project], tasks: list[Task]) -> str:
        launch_project = next((project for project in projects if "launch" in project.name.casefold()), None)
        if launch_project:
            return f"Move {launch_project.name} forward with one concrete launch outcome."
        if projects:
            return f"Keep momentum on {projects[0].name}."
        if tasks:
            return f"Complete {tasks[0].title} and preserve the next step."
        return "Build one clear anchor for your work today."

    @staticmethod
    def _focus_from_workspace(projects: list[Project], tasks: list[Task], continuity_cards) -> str:
        project = next((item for item in projects if item.current_focus), None)
        if project:
            return project.current_focus
        if tasks:
            return tasks[0].title
        if continuity_cards:
            return continuity_cards[0].title
        if projects:
            return projects[0].recommended_next_step or projects[0].name
        return "Capture the first priority Synzept should track."

    @staticmethod
    def _split_lines(value: str | None) -> list[str]:
        if not value:
            return []
        return [line.strip(" -*\t") for line in value.replace(";", "\n").splitlines() if line.strip(" -*\t")]

    @staticmethod
    def _return_context(
        *,
        decisions: list[Decision],
        open_loops: list[ReturnOpenLoopOut],
        notes: list[Note],
        project_names: dict,
    ) -> list[ReturnContextOut]:
        context: list[ReturnContextOut] = []
        for decision in decisions:
            if decision.status != "pending":
                continue
            project_name = project_names.get(decision.project_id, "Workspace")
            context.append(
                ReturnContextOut(
                    title=decision.title,
                    detail=f"Pending decision in {project_name}.",
                    type="pending_decision",
                    href=f"/projects/{decision.project_id}",
                )
            )
        for loop in open_loops:
            if loop.priority != "high" and loop.type != "blocked_work":
                continue
            context.append(
                ReturnContextOut(
                    title=loop.title,
                    detail=loop.description or loop.next_step,
                    type=loop.type,
                    href=loop.href,
                )
            )
        for note in notes[:4]:
            text = f"{note.title or ''} {note.summary or ''} {note.content}".casefold()
            if not any(marker in text for marker in ("important", "remember", "critical", "blocked", "pending")):
                continue
            context.append(
                ReturnContextOut(
                    title=note.title or "Important note",
                    detail=truncate(note.summary or note.content, 120),
                    type="note",
                    href="/notes",
                )
            )
        return context[:6]

    @staticmethod
    def _activity_href(item: RecentActivityOut) -> str:
        if item.type == "conversation":
            return f"/chat?conversation={item.id}"
        if item.type == "project" and item.project_id:
            return f"/projects/{item.project_id}"
        if item.type == "note":
            return "/notes"
        if item.type == "task":
            return "/tasks"
        return "/dashboard"

    @staticmethod
    def _after(value, since: datetime) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return False
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        return value > since

    @staticmethod
    def _sort_timestamp(value: datetime) -> float:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.timestamp()
