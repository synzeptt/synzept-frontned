from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.goal import Goal
from app.models.project import Project
from app.models.project_intelligence_phase2 import Decision, OpenLoop
from app.models.task import Task
from app.models.timeline_event import TimelineEvent
from app.models.workspace_activity import WorkspaceActivity
from app.schemas.agent_memory import AgentMemoryItemOut, AgentMemoryTimelineOut
from app.tasks.service import OPEN_STATUSES


class AgentMemoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def timeline(self, user_id: UUID, *, days: int = 90, limit: int = 80) -> AgentMemoryTimelineOut:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        activities = await self._activities(user_id, since, limit=limit)
        explicit_events = await self._timeline_events(user_id, since, limit=limit)
        conversations = await self._important_conversations(user_id, since, limit=20)
        decisions = await self._decisions(user_id, limit=30)
        goals = await self._goals(user_id)
        tasks = await self._tasks(user_id)
        open_loops = await self._open_loops(user_id)
        projects = await self._projects(user_id)

        items = [
            *[self._activity_item(item) for item in activities],
            *[self._timeline_item(item) for item in explicit_events],
            *[self._conversation_item(item) for item in conversations],
            *[self._decision_item(item) for item in decisions],
        ]
        items.sort(key=lambda item: item.happened_at, reverse=True)
        items = items[:limit]

        incomplete_goals = [goal.title for goal in goals if goal.status != "completed"]
        important_decisions = [decision.title for decision in decisions if decision.status in {"decided", "accepted", "closed"} or decision.description]
        unfinished = self._unfinished(goals, tasks, open_loops, conversations)
        changed = [self._changed_label(item) for item in items[:8]]

        return AgentMemoryTimelineOut(
            items=items,
            what_changed=changed,
            unfinished=unfinished[:8],
            recommended_next_step=self._recommended_next_step(tasks, open_loops, goals, projects),
            incomplete_goals=incomplete_goals[:8],
            important_decisions=important_decisions[:8],
            recall_prompts=[
                "What was I working on last week?",
                "What changed this month?",
                "What goals are still incomplete?",
                "What important decisions have I made?",
            ],
        )

    async def _activities(self, user_id: UUID, since: datetime, *, limit: int) -> list[WorkspaceActivity]:
        result = await self.session.execute(
            select(WorkspaceActivity)
            .where(WorkspaceActivity.user_id == user_id, WorkspaceActivity.created_at >= since)
            .order_by(WorkspaceActivity.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def _timeline_events(self, user_id: UUID, since: datetime, *, limit: int) -> list[TimelineEvent]:
        result = await self.session.execute(
            select(TimelineEvent)
            .where(TimelineEvent.user_id == user_id, TimelineEvent.created_at >= since)
            .order_by(TimelineEvent.event_date.desc(), TimelineEvent.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def _important_conversations(self, user_id: UUID, since: datetime, *, limit: int) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
                Conversation.updated_at >= since,
            )
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        return [item for item in result.scalars() if item.summary or item.active_intent]

    async def _decisions(self, user_id: UUID, *, limit: int) -> list[Decision]:
        result = await self.session.execute(
            select(Decision)
            .join(Project, Project.id == Decision.project_id)
            .where(Project.user_id == user_id, Project.deleted_at.is_(None))
            .order_by(Decision.updated_at.desc(), Decision.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def _goals(self, user_id: UUID) -> list[Goal]:
        result = await self.session.execute(
            select(Goal).where(Goal.user_id == user_id, Goal.deleted_at.is_(None)).order_by(Goal.updated_at.desc())
        )
        return list(result.scalars())

    async def _tasks(self, user_id: UUID) -> list[Task]:
        result = await self.session.execute(
            select(Task).where(Task.user_id == user_id, Task.deleted_at.is_(None)).order_by(Task.updated_at.desc())
        )
        return list(result.scalars())

    async def _open_loops(self, user_id: UUID) -> list[OpenLoop]:
        result = await self.session.execute(
            select(OpenLoop)
            .join(Project, Project.id == OpenLoop.project_id)
            .where(Project.user_id == user_id, Project.deleted_at.is_(None), OpenLoop.status == "open")
            .order_by(OpenLoop.updated_at.desc(), OpenLoop.created_at.desc())
        )
        return list(result.scalars())

    async def _projects(self, user_id: UUID) -> list[Project]:
        result = await self.session.execute(
            select(Project).where(Project.user_id == user_id, Project.deleted_at.is_(None)).order_by(Project.updated_at.desc())
        )
        return list(result.scalars())

    def _activity_item(self, item: WorkspaceActivity) -> AgentMemoryItemOut:
        return AgentMemoryItemOut(
            id=f"activity:{item.id}",
            type=item.action,
            title=item.title,
            detail=item.detail or "",
            happened_at=self._as_utc(item.created_at),
            why_it_mattered=self._why(item.action, item.title),
            project_id=item.project_id,
            goal_id=item.goal_id,
            task_id=item.task_id,
            note_id=item.note_id,
        )

    def _timeline_item(self, item: TimelineEvent) -> AgentMemoryItemOut:
        return AgentMemoryItemOut(
            id=f"timeline:{item.id}",
            type=f"timeline_{item.event_type}",
            title=item.title,
            detail=item.description or "",
            happened_at=self._as_utc(item.created_at),
            why_it_mattered=item.description or "This was recorded as a timeline event for future recall.",
            project_id=item.project_id,
        )

    def _conversation_item(self, item: Conversation) -> AgentMemoryItemOut:
        detail = item.summary or item.active_intent or ""
        return AgentMemoryItemOut(
            id=f"conversation:{item.id}",
            type="important_conversation",
            title=item.title or "Important conversation",
            detail=detail,
            happened_at=self._as_utc(item.updated_at),
            why_it_mattered=item.active_intent or "This conversation preserved context the Agent can help resume.",
            project_id=item.project_id,
        )

    def _decision_item(self, item: Decision) -> AgentMemoryItemOut:
        return AgentMemoryItemOut(
            id=f"decision:{item.id}",
            type="decision",
            title=item.title,
            detail=item.description or f"Status: {item.status}",
            happened_at=self._as_utc(item.updated_at),
            why_it_mattered=item.description or "This decision changes how the related project should move forward.",
            project_id=item.project_id,
        )

    def _unfinished(
        self,
        goals: list[Goal],
        tasks: list[Task],
        open_loops: list[OpenLoop],
        conversations: list[Conversation],
    ) -> list[str]:
        return [
            *[f"Goal: {goal.title}" for goal in goals if goal.status != "completed"],
            *[f"Task: {task.title}" for task in tasks if task.status in OPEN_STATUSES],
            *[f"Open loop: {item.title}" for item in open_loops],
            *[f"Conversation: {item.active_intent}" for item in conversations if item.active_intent],
        ]

    def _recommended_next_step(
        self,
        tasks: list[Task],
        open_loops: list[OpenLoop],
        goals: list[Goal],
        projects: list[Project],
    ) -> str:
        priority = {"high": 3, "medium": 2, "low": 1}
        open_tasks = [task for task in tasks if task.status in OPEN_STATUSES]
        open_tasks.sort(key=lambda task: (priority.get(task.priority or "low", 0), self._as_utc(task.updated_at)), reverse=True)
        if open_tasks:
            return open_tasks[0].title
        if open_loops:
            return f"Resolve {open_loops[0].title}"
        active_goals = [goal for goal in goals if goal.status != "completed"]
        if active_goals:
            return f"Define the next step for {active_goals[0].title}"
        active_projects = [project for project in projects if project.status == "active"]
        if active_projects:
            return active_projects[0].recommended_next_step or f"Update {active_projects[0].name}"
        return "Ask Synzept Agent what to focus on next."

    @staticmethod
    def _changed_label(item: AgentMemoryItemOut) -> str:
        return f"{item.title} ({item.type.replace('_', ' ')})"

    @staticmethod
    def _why(action: str, title: str) -> str:
        labels = {
            "goal_created": "This created a desired outcome the Agent should optimize around.",
            "goal_completed": "This shows progress and reduces unfinished context.",
            "project_created": "This added a new work track the Agent should remember.",
            "project_updated": "This changed the state of an active work track.",
            "decision_created": "This captured a decision the Agent should not ask you to remake.",
            "decision_updated": "This changed a decision that affects future recommendations.",
            "milestone_created": "This added a checkpoint toward a goal.",
            "milestone_completed": "This completed a checkpoint and changed progress.",
            "open_loop_created": "This captured unfinished work that should come back later.",
            "task_completed": "This closed an action and changed what remains.",
            "note_created": "This saved context the Agent can reference later.",
        }
        return labels.get(action, f"This changed the remembered context for {title}.")

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
