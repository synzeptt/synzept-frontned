from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.goal import Goal
from app.models.graph import GraphEdge, GraphNode
from app.models.learning import LearningObservation, LearningSuggestion
from app.models.learning_signal import LearningSignal
from app.models.memory import Memory
from app.models.project import Project
from app.models.project_intelligence import ProjectDecision, ProjectOpenLoop
from app.models.task import Task
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.models.workspace_activity import WorkspaceActivity
from app.schemas.continuity_assistant import (
    AssistantRecommendationOut,
    ContinuityAssistantOut,
    EvidenceCountOut,
    ExplainedPatternOut,
    HiddenConnectionOut,
    ProjectRiskOut,
    TurningPointOut,
)
from app.tasks.service import OPEN_STATUSES

TURNING_POINT_TYPES = {"launch", "strategy_change", "milestone", "customer", "decision", "major_milestone"}
STOP_WORDS = {"active", "architecture", "build", "complete", "project", "system", "the", "this", "with"}


class ContinuityAssistantService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def overview(self, user: User) -> ContinuityAssistantOut:
        context = await self._context(user.id)
        priorities = self._priorities(context)
        open_loops = self._open_loops(context)
        recommendation = self._recommendation(context)
        return ContinuityAssistantOut(
            greeting=f"Good morning, {user.display_name or 'there'}.",
            summary=self._summary(priorities, open_loops, context),
            priorities=priorities[:3],
            open_loops=open_loops[:4],
            recent_progress=self._recent_progress(context)[:4],
            key_context=self._key_context(context)[:3],
            recommendation=recommendation,
            learned_patterns=self._learned_patterns(context)[:3],
            project_risks=self._project_risks(context)[:3],
            turning_points=self._turning_points(context)[:3],
            hidden_connections=self._hidden_connections(context)[:3],
        )

    async def recommend_next_step(self, user_id: UUID) -> AssistantRecommendationOut:
        return self._recommendation(await self._context(user_id))

    async def _context(self, user_id: UUID) -> dict:
        async def rows(model, *conditions, order_by=None, limit=None):
            statement = select(model).where(*conditions)
            if order_by is not None:
                statement = statement.order_by(order_by)
            if limit:
                statement = statement.limit(limit)
            return list((await self.session.execute(statement)).scalars())

        projects = await rows(Project, Project.user_id == user_id, Project.deleted_at.is_(None), order_by=Project.updated_at.desc())
        project_ids = [item.id for item in projects]
        return {
            "projects": projects,
            "goals": await rows(Goal, Goal.user_id == user_id, Goal.deleted_at.is_(None), order_by=Goal.updated_at.desc()),
            "tasks": await rows(Task, Task.user_id == user_id, Task.deleted_at.is_(None), order_by=Task.updated_at.desc()),
            "memories": await rows(Memory, Memory.user_id == user_id, Memory.deleted_at.is_(None), order_by=Memory.updated_at.desc(), limit=40),
            "understanding": await rows(UserUnderstanding, UserUnderstanding.user_id == user_id, order_by=UserUnderstanding.updated_at.desc()),
            "timeline": await rows(TimelineEvent, TimelineEvent.user_id == user_id, order_by=TimelineEvent.event_date.desc(), limit=40),
            "learning_signals": await rows(LearningSignal, LearningSignal.user_id == user_id, order_by=LearningSignal.updated_at.desc(), limit=40),
            "learning_suggestions": await rows(LearningSuggestion, LearningSuggestion.user_id == user_id, LearningSuggestion.status == "accepted", order_by=LearningSuggestion.created_at.desc(), limit=20),
            "observations": await rows(LearningObservation, LearningObservation.user_id == user_id, order_by=LearningObservation.created_at.desc(), limit=120),
            "conversations": await rows(Conversation, Conversation.user_id == user_id, Conversation.deleted_at.is_(None), order_by=Conversation.updated_at.desc(), limit=20),
            "activities": await rows(WorkspaceActivity, WorkspaceActivity.user_id == user_id, order_by=WorkspaceActivity.created_at.desc(), limit=120),
            "decisions": await rows(ProjectDecision, ProjectDecision.project_id.in_(project_ids)) if project_ids else [],
            "loops": await rows(ProjectOpenLoop, ProjectOpenLoop.project_id.in_(project_ids)) if project_ids else [],
            "nodes": await rows(GraphNode, GraphNode.user_id == user_id, order_by=GraphNode.created_at.desc(), limit=80),
            "edges": await rows(GraphEdge, GraphEdge.user_id == user_id, order_by=GraphEdge.created_at.desc(), limit=120),
            "now": datetime.now(timezone.utc),
        }

    def _priorities(self, context: dict) -> list[str]:
        items: list[str] = []
        for item in context["understanding"]:
            if item.title in {"Current Priorities", "Short-Term Goals", "Active Projects"}:
                items.extend(self._split(item.value))
        items.extend(item.title for item in context["goals"] if item.status == "active")
        items.extend(item.name for item in context["projects"] if item.status == "active")
        return self._unique(items)

    def _open_loops(self, context: dict) -> list[str]:
        items = [item.loop for item in context["loops"] if item.status == "open"]
        items.extend(item.decision for item in context["decisions"] if item.status == "open")
        items.extend(item.title for item in context["tasks"] if item.status in OPEN_STATUSES)
        items.extend(item.active_intent for item in context["conversations"] if item.active_intent)
        return self._unique(items)

    def _recommendation(self, context: dict) -> AssistantRecommendationOut:
        now = context["now"]
        tasks = [item for item in context["tasks"] if item.status in OPEN_STATUSES]
        overdue = [item for item in tasks if item.due_at and self._as_utc(item.due_at) < now]
        if overdue:
            task = sorted(overdue, key=lambda item: (item.due_at, item.priority != "high"))[0]
            return AssistantRecommendationOut(title=task.title, detail=f"Complete {task.title} before starting new work.", reason="This task is overdue and is the clearest source of avoidable drag.")
        updates = Counter(item.task_id for item in context["activities"] if item.task_id and item.action == "task_updated")
        repeated = next((item for item in tasks if updates[item.id] >= 2), None)
        if repeated:
            return AssistantRecommendationOut(title=f"Schedule a focused review for {repeated.title}", detail=f"Resolve {repeated.title} in a dedicated work block before adding another priority.", reason=f"This open item has been revisited {updates[repeated.id]} times without completion.")
        risks = self._project_risks(context)
        if risks:
            risk = risks[0]
            return AssistantRecommendationOut(title=f"Review {risk.project_title}", detail=f"Unblock {risk.project_title} before beginning another project.", reason=risk.reasons[0])
        decision = next((item for item in context["decisions"] if item.status == "open"), None)
        if decision:
            return AssistantRecommendationOut(title=f"Resolve {decision.decision}", detail=f"Finalize {decision.decision} before beginning dependent work.", reason="An unresolved decision can create rework across the project.")
        loop = next((item for item in context["loops"] if item.status == "open"), None)
        if loop:
            return AssistantRecommendationOut(title=f"Close {loop.loop}", detail=f"Finish {loop.loop} before opening another thread.", reason="This unfinished thread is already visible in project context.")
        goal = next((item for item in context["goals"] if item.status == "active"), None)
        if goal:
            return AssistantRecommendationOut(title=f"Define the next action for {goal.title}", detail=f"Choose one concrete task that moves {goal.title} forward today.", reason="This active goal needs a specific next move.")
        return AssistantRecommendationOut(title="Choose one meaningful priority", detail="Set one concrete outcome for today before adding more work.", reason="A single clear priority gives Synzept enough context to help.")

    def _recent_progress(self, context: dict) -> list[str]:
        since = context["now"] - timedelta(days=7)
        items = [item.title for item in context["timeline"] if item.event_date >= since.date()]
        items.extend(item.title for item in context["activities"] if self._as_utc(item.created_at) >= since and item.action in {"task_completed", "milestone_completed", "goal_completed", "project_updated"})
        return self._unique(items)

    def _key_context(self, context: dict) -> list[str]:
        items = [item.value for item in context["understanding"] if item.category in {"preferences", "learned_insights"}]
        items.extend(item.summary or item.content for item in context["memories"] if item.confidence >= 0.7)
        return self._unique(items)

    def _project_risks(self, context: dict) -> list[ProjectRiskOut]:
        now = context["now"]
        decisions = defaultdict(list)
        loops = defaultdict(list)
        tasks = defaultdict(list)
        for item in context["decisions"]:
            if item.status == "open":
                decisions[item.project_id].append(item)
        for item in context["loops"]:
            if item.status == "open":
                loops[item.project_id].append(item)
        for item in context["tasks"]:
            if item.status in OPEN_STATUSES:
                tasks[item.project_id].append(item)
        result = []
        for project in context["projects"]:
            if project.status != "active":
                continue
            days = self._inactive_days(project.updated_at, now)
            reasons = []
            if days >= 7:
                reasons.append(f"No activity has been recorded for {days} days.")
            if decisions[project.id]:
                reasons.append(f"{len(decisions[project.id])} decision(s) remain unresolved.")
            overdue = sum(bool(item.due_at and self._as_utc(item.due_at) < now) for item in tasks[project.id])
            if overdue:
                reasons.append(f"{overdue} overdue task(s) need attention.")
            if loops[project.id]:
                reasons.append(f"{len(loops[project.id])} open loop(s) remain unfinished.")
            if reasons:
                result.append(ProjectRiskOut(project_id=str(project.id), project_title=project.name, risk="high" if days >= 14 or overdue else "medium", reasons=reasons))
        return sorted(result, key=lambda item: item.risk == "high", reverse=True)

    def _learned_patterns(self, context: dict) -> list[ExplainedPatternOut]:
        result = []
        for suggestion in context["learning_suggestions"]:
            terms = [part for part in re.findall(r"[a-z0-9]+", suggestion.title.casefold()) if part not in STOP_WORDS]
            matching = [item for item in context["observations"] if any(term in item.content.casefold() for term in terms)]
            counts = Counter(item.source for item in matching)
            evidence = [EvidenceCountOut(source=source.replace("_", " "), count=count) for source, count in counts.most_common(4)]
            result.append(ExplainedPatternOut(title=suggestion.title, explanation=suggestion.description, confidence=suggestion.confidence, evidence=evidence))
        for signal in context["learning_signals"]:
            result.append(ExplainedPatternOut(title=signal.signal_type.replace("_", " ").title(), explanation=signal.content, confidence=signal.confidence, evidence=[]))
        return result

    def _turning_points(self, context: dict) -> list[TurningPointOut]:
        events = [item for item in context["timeline"] if item.importance >= 0.75 or item.event_type in TURNING_POINT_TYPES]
        return [TurningPointOut(event_type=item.event_type, title=item.title, description=item.description, event_date=item.event_date.isoformat()) for item in events]

    def _hidden_connections(self, context: dict) -> list[HiddenConnectionOut]:
        nodes = context["nodes"]
        edges = context["edges"]
        adjacency = defaultdict(set)
        for edge in edges:
            adjacency[edge.source_node_id].add(edge.target_node_id)
            adjacency[edge.target_node_id].add(edge.source_node_id)
        result = []
        for index, left in enumerate(nodes):
            left_words = self._keywords(left.title)
            for right in nodes[index + 1:]:
                shared = sorted(left_words & self._keywords(right.title))
                if shared and right.id not in adjacency[left.id]:
                    result.append(HiddenConnectionOut(title=f"{left.title} and {right.title}", detail=f"Potential shared work opportunity detected around {', '.join(shared[:3])}.", node_titles=[left.title, right.title]))
        return result

    @staticmethod
    def _summary(priorities: list[str], open_loops: list[str], context: dict) -> str:
        changes = len(ContinuityAssistantService._recent_progress_static(context))
        return f"You have {len(priorities[:3])} active priorities, {len(open_loops[:4])} visible open loops, and {changes} recent progress update(s)."

    @staticmethod
    def _recent_progress_static(context: dict) -> list[str]:
        since = context["now"] - timedelta(days=7)
        return [item.title for item in context["timeline"] if item.event_date >= since.date()]

    @staticmethod
    def _keywords(value: str) -> set[str]:
        return {item for item in re.findall(r"[a-z0-9]+", value.casefold()) if len(item) > 2 and item not in STOP_WORDS}

    @staticmethod
    def _split(value: str) -> list[str]:
        return [item.strip(" -*\t") for item in value.replace(";", "\n").splitlines() if item.strip(" -*\t")]

    @staticmethod
    def _unique(items) -> list[str]:
        result, seen = [], set()
        for item in items:
            key = item.strip().casefold()
            if key and key not in seen:
                seen.add(key)
                result.append(item.strip())
        return result

    @staticmethod
    def _inactive_days(value: datetime, now: datetime) -> int:
        return max(0, (now - ContinuityAssistantService._as_utc(value)).days)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
