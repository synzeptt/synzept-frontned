from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.memory_service import MemoryService
from app.models.note import Note
from app.models.project import Project
from app.models.task import Task
from app.models.user_understanding import UserUnderstanding
from app.models.workspace_activity import WorkspaceActivity
from app.schemas.reasoning import ReasoningAnalysisOut, ReasoningInsightOut
from app.services.goal_progress_service import GoalProgressService
from app.services.open_loops_engine_service import OpenLoopsEngineService
from app.services.relationship_graph_phase5_service import RelationshipGraphPhase5Service
from app.services.workspace_service import WorkspaceService
from app.services.user_understanding_service import UserUnderstandingService
from app.tasks.service import OPEN_STATUSES


@dataclass
class ReasoningContext:
    projects: list[Project]
    goals: list[Any]
    tasks: list[Task]
    notes: list[Note]
    memories: list[Any]
    activities: list[WorkspaceActivity]
    understanding: list[UserUnderstanding]
    open_loop_items: list[Any]
    graph_context: Any
    now: datetime


class ReasoningService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.workspace_service = WorkspaceService(session)
        self.goal_service = GoalProgressService(session)
        self.open_loops_service = OpenLoopsEngineService(session)
        self.graph_service = RelationshipGraphPhase5Service(session)
        self.memory_service = MemoryService(session)
        self.understanding_service = UserUnderstandingService(session)

    async def analysis(self, user_id: UUID) -> ReasoningAnalysisOut:
        context = await self._context(user_id)
        priorities = self._priorities(context)
        blockers = self._blockers(context)
        opportunities = self._opportunities(context)
        progress = self._progress(context)
        missing_context = self._missing_context(context)
        highest_priority = priorities[0].title if priorities else None
        suggested_next_action = priorities[0].detail if priorities else self._fallback_next_action(context)
        confidence_score = self._confidence_score(context, priorities, blockers, opportunities, missing_context)
        why_it_matters = self._why_it_matters(context, priorities, blockers, opportunities, missing_context)

        return ReasoningAnalysisOut(
            generated_at=context.now,
            confidence_score=confidence_score,
            suggested_next_action=suggested_next_action,
            highest_priority=highest_priority,
            why_it_matters=why_it_matters,
            priorities=priorities[:6],
            blockers=blockers[:6],
            opportunities=opportunities[:6],
            progress=progress[:5],
            missing_context=missing_context[:4],
        )

    async def priorities(self, user_id: UUID) -> list[ReasoningInsightOut]:
        return self._priorities(await self._context(user_id))

    async def blockers(self, user_id: UUID) -> list[ReasoningInsightOut]:
        return self._blockers(await self._context(user_id))

    async def opportunities(self, user_id: UUID) -> list[ReasoningInsightOut]:
        return self._opportunities(await self._context(user_id))

    async def progress(self, user_id: UUID) -> list[ReasoningInsightOut]:
        return self._progress(await self._context(user_id))

    async def missing_context(self, user_id: UUID) -> list[str]:
        return self._missing_context(await self._context(user_id))

    async def _context(self, user_id: UUID) -> ReasoningContext:
        project_rows = await self.workspace_service._projects(user_id)
        goals = await self.goal_service.list_goals(user_id)
        tasks = await self.workspace_service._tasks(user_id)
        notes = await self.workspace_service._notes(user_id)
        memories = await self.memory_service.search_memory(user_id=user_id, limit=40)
        activities = await self.workspace_service.timeline(user_id, limit=120)
        understanding = await self._understanding(user_id)
        open_loops = (await self.open_loops_service.list(user_id)).items
        graph_context = await self.graph_service.context_for_query(user_id, "priority")
        return ReasoningContext(
            projects=project_rows,
            goals=goals,
            tasks=tasks,
            notes=notes,
            memories=memories,
            activities=activities,
            understanding=understanding,
            open_loop_items=open_loops,
            graph_context=graph_context,
            now=datetime.now(timezone.utc),
        )

    async def _understanding(self, user_id: UUID) -> list[UserUnderstanding]:
        result = await self.session.execute(
            select(UserUnderstanding).where(UserUnderstanding.user_id == user_id).order_by(UserUnderstanding.updated_at.desc()).limit(120)
        )
        return list(result.scalars())

    def _priorities(self, context: ReasoningContext) -> list[ReasoningInsightOut]:
        items: list[ReasoningInsightOut] = []
        focus_items = [item for item in context.understanding if item.category in {"current_focus", "priorities", "short_term_goals", "missions"}]
        if focus_items:
            for item in focus_items[:3]:
                if item.value.strip():
                    items.append(self._insight(
                        type="understanding_priority",
                        title=item.value,
                        detail=f"Captured from your understanding of {item.title}.",
                        priority="high",
                        evidence=[item.category],
                        confidence=min((item.confidence or 0.7) + 0.1, 1.0),
                    ))

        for goal in [goal for goal in context.goals if goal.status == "active"]:
            detail = f"{round(goal.progress)}% complete." if getattr(goal, "progress", None) is not None else "Active goal."
            items.append(self._insight(
                type="goal_priority",
                title=goal.title,
                detail=f"{detail} Move this goal forward with the next milestone.",
                priority="high",
                project_id=goal.project_id,
                confidence=0.78,
            ))

        for task in [task for task in context.tasks if task.status in OPEN_STATUSES]:
            if task.due_at and task.due_at < context.now:
                detail = "Overdue task that is blocking progress."
                priority = "high"
            elif task.priority == "high":
                detail = "High-priority task that should be resolved soon."
                priority = "high"
            else:
                detail = "Open task that can move work forward."
                priority = "medium"
            items.append(self._insight(
                type="task_priority",
                title=task.title,
                detail=detail,
                priority=priority,
                project_id=task.project_id,
                task_id=task.id,
                confidence=0.7,
            ))

        for item in context.open_loop_items:
            items.append(self._insight(
                type="open_loop_priority",
                title=item.title,
                detail=item.description or "This open loop should be closed to restore momentum.",
                priority="high" if item.priority == "high" else "medium",
                project_id=item.projectId,
                confidence=0.75,
            ))

        for graph_item in context.graph_context.nextActions:
            items.append(self._insight(
                type="graph_next_action",
                title=graph_item.title,
                detail=graph_item.reason or "Graph analysis identified this as a strong next action.",
                priority="medium",
                node_id=graph_item.nodeId,
                confidence=0.72,
            ))

        if not items and context.projects:
            project = context.projects[0]
            items.append(self._insight(
                type="project_priority",
                title=project.name,
                detail=project.recommended_next_step or project.current_focus or "Choose the next concrete move for this project.",
                priority="medium",
                project_id=project.id,
                confidence=0.6,
            ))

        return self._sort_insights(items)

    def _blockers(self, context: ReasoningContext) -> list[ReasoningInsightOut]:
        items: list[ReasoningInsightOut] = []
        for task in [task for task in context.tasks if task.status in OPEN_STATUSES and task.due_at and task.due_at < context.now]:
            items.append(self._insight(
                type="overdue_task",
                title=task.title,
                detail="Overdue tasks create immediate drag and risk missing deadlines.",
                severity="attention",
                priority="high",
                project_id=task.project_id,
                task_id=task.id,
                confidence=0.9,
            ))

        for item in context.open_loop_items:
            if item.status == "open":
                items.append(self._insight(
                    type="open_loop",
                    title=item.title,
                    detail=item.description or "An unresolved item is competing for attention.",
                    severity="attention" if item.priority == "high" else "warning",
                    priority=item.priority,
                    project_id=item.projectId,
                    confidence=0.78,
                ))

        for graph_item in context.graph_context.blockers:
            items.append(self._insight(
                type="graph_blocker",
                title=graph_item.title,
                detail=graph_item.reason or "The knowledge graph surfaces this blocker.",
                severity="warning",
                priority="high",
                node_id=graph_item.nodeId,
                confidence=0.7,
            ))

        stalled_projects = [project for project in context.projects if project.status == "active" and self._inactive_days(project.updated_at, context.now) >= 7]
        for project in stalled_projects:
            items.append(self._insight(
                type="stalled_project",
                title=project.name,
                detail=f"No updates for {self._inactive_days(project.updated_at, context.now)} days.",
                severity="warning",
                priority="medium",
                project_id=project.id,
                confidence=0.68,
            ))

        return self._sort_insights(items)

    def _opportunities(self, context: ReasoningContext) -> list[ReasoningInsightOut]:
        items: list[ReasoningInsightOut] = []
        for graph_item in context.graph_context.supportingContext[:4]:
            items.append(self._insight(
                type="graph_opportunity",
                title=graph_item.title,
                detail=graph_item.reason or graph_item.description or "A related item could support your current work.",
                priority="medium",
                node_id=graph_item.nodeId,
                confidence=0.7,
            ))

        launch_projects = [project for project in context.projects if "launch" in f"{project.name} {project.description or ''} {project.current_focus}".casefold()]
        if launch_projects:
            items.append(self._insight(
                type="launch_opportunity",
                title="Turn launch work into momentum.",
                detail="Focus on customer or distribution next to make launch work pay off.",
                priority="high",
                confidence=0.75,
            ))

        if any(item for item in context.memories if (item.category or item.memory_type) in {"interests", "skills"}):
            items.append(self._insight(
                type="learning_opportunity",
                title="Leverage a remembered interest or skill.",
                detail="Connect learning and active work to generate momentum from existing knowledge.",
                priority="medium",
                confidence=0.68,
            ))

        if context.open_loop_items and len(context.open_loop_items) < 3:
            items.append(self._insight(
                type="clarity_opportunity",
                title="Use open loops to shape your next action.",
                detail="Closing a small set of open loops can create space for higher-value work.",
                priority="medium",
                confidence=0.64,
            ))

        return self._sort_insights(items)

    def _progress(self, context: ReasoningContext) -> list[ReasoningInsightOut]:
        items: list[ReasoningInsightOut] = []
        recent_completions = [activity for activity in context.activities if getattr(activity, "action", "") in {"task_completed", "milestone_completed", "goal_completed"} and self._as_utc(getattr(activity, "created_at", context.now)) >= context.now - timedelta(days=7)]
        if recent_completions:
            items.append(self._insight(
                type="recent_progress",
                title="Recent completions have been recorded.",
                detail=f"{len(recent_completions)} completion(s) were recorded in the last 7 days.",
                priority="medium",
                confidence=0.75,
            ))
        if context.goals:
            active_goals = [goal for goal in context.goals if goal.status == "active"]
            if active_goals:
                average_progress = round(sum((getattr(goal, "progress", 0) or 0) for goal in active_goals) / len(active_goals), 1)
                items.append(self._insight(
                    type="goal_progress",
                    title="Goal progress summary.",
                    detail=f"Average progress across active goals is {average_progress}%.",
                    priority="medium",
                    confidence=0.72,
                ))
            else:
                items.append(self._insight(
                    type="no_active_goals",
                    title="No active goals currently defined.",
                    detail="Create a goal to make progress more visible and easier to prioritize.",
                    severity="warning",
                    priority="medium",
                    confidence=0.6,
                ))
        else:
            items.append(self._insight(
                type="no_goals",
                title="No goals captured yet.",
                detail="Define at least one goal so progress can be tracked meaningfully.",
                severity="warning",
                priority="medium",
                confidence=0.58,
            ))

        if any(task for task in context.tasks if task.status in OPEN_STATUSES and self._inactive_days(task.updated_at, context.now) >= 7):
            items.append(self._insight(
                type="stalled_task",
                title="Open tasks have not been updated recently.",
                detail="Revisit stale work to avoid hidden scope creep.",
                severity="warning",
                priority="medium",
                confidence=0.66,
            ))

        return self._sort_insights(items)

    def _missing_context(self, context: ReasoningContext) -> list[str]:
        missing: list[str] = []
        if not any(item.category in {"current_focus", "priorities", "short_term_goals", "missions"} for item in context.understanding):
            missing.append("No active focus or priority has been captured.")
        if not any(goal.status == "active" for goal in context.goals):
            missing.append("No active goals are defined.")
        if not context.tasks and not context.open_loop_items:
            missing.append("No tasks or open loops are available to anchor the reasoning.")
        if not any(self._as_utc(getattr(activity, "created_at", context.now)) >= context.now - timedelta(days=7) for activity in context.activities):
            missing.append("No recent workspace activity was recorded in the last 7 days.")
        if not context.memories:
            missing.append("No memories are available for contextual grounding.")
        return missing

    def _why_it_matters(
        self,
        context: ReasoningContext,
        priorities: list[ReasoningInsightOut],
        blockers: list[ReasoningInsightOut],
        opportunities: list[ReasoningInsightOut],
        missing_context: list[str],
    ) -> list[str]:
        lines: list[str] = []
        if blockers:
            lines.append(f"{len(blockers)} blocker(s) are likely to slow your progress if left unresolved.")
        if priorities:
            lines.append(f"Top priorities are drawn from your active work, meaning the reasoning reflects recent user and project signals.")
        if opportunities:
            lines.append("Hidden connections in your knowledge graph reveal additional support and next-action possibilities.")
        if missing_context:
            lines.append("Missing context will reduce the confidence of recommendations until key goals or priorities are clarified.")
        if not lines:
            lines.append("This analysis is based on current goals, tasks, open loops, and graph context.")
        return lines[:4]

    def _confidence_score(
        self,
        context: ReasoningContext,
        priorities: list[ReasoningInsightOut],
        blockers: list[ReasoningInsightOut],
        opportunities: list[ReasoningInsightOut],
        missing_context: list[str],
    ) -> float:
        score = 0.3
        score += 0.1 if context.goals else 0.0
        score += 0.1 if context.tasks else 0.0
        score += 0.1 if context.projects else 0.0
        score += 0.05 if context.open_loop_items else 0.0
        score += 0.05 if context.graph_context.currentEntities else 0.0
        score += 0.1 if context.understanding else 0.0
        score += min(len(priorities), 2) * 0.05
        score += min(len(blockers), 2) * 0.03
        score += min(len(opportunities), 2) * 0.02
        score -= min(len(missing_context), 3) * 0.06
        return round(max(min(score, 1.0), 0.2), 2)

    def _fallback_next_action(self, context: ReasoningContext) -> str:
        if context.tasks:
            task = next((task for task in context.tasks if task.status in OPEN_STATUSES), None)
            if task:
                return f"Continue with {task.title}."
        if context.goals:
            return f"Move forward on {context.goals[0].title}."
        return "Define a concrete priority so Synzept can recommend your next action."

    def _sort_insights(self, items: list[ReasoningInsightOut]) -> list[ReasoningInsightOut]:
        def score(item: ReasoningInsightOut) -> float:
            base = item.confidence or 0.5
            if item.priority == "high":
                base += 0.15
            if item.severity == "attention":
                base += 0.1
            return base

        unique: dict[str, ReasoningInsightOut] = {}
        for item in items:
            key = item.title.casefold()
            if key not in unique:
                unique[key] = item
        return sorted(unique.values(), key=lambda item: score(item), reverse=True)

    def _insight(
        self,
        *,
        type: str,
        title: str,
        detail: str,
        severity: str = "info",
        priority: str = "medium",
        project_id: UUID | None = None,
        goal_id: UUID | None = None,
        task_id: UUID | None = None,
        node_id: UUID | None = None,
        evidence: list[str] | None = None,
        confidence: float = 0.65,
    ) -> ReasoningInsightOut:
        return ReasoningInsightOut(
            type=type,
            title=title,
            detail=detail,
            severity=severity,
            priority=priority,
            project_id=project_id,
            goal_id=goal_id,
            task_id=task_id,
            node_id=node_id,
            evidence=evidence or [],
            confidence=min(max(confidence, 0.2), 1.0),
        )

    @staticmethod
    def _inactive_days(value: datetime | None, now: datetime) -> int:
        if not value:
            return 0
        return max(0, (now - value).days)

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
