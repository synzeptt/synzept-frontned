from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.memory_service import MemoryService
from app.models.goal import Goal
from app.models.memory import Memory
from app.models.note import Note
from app.models.project import Project
from app.models.task import Task
from app.models.workspace_activity import WorkspaceActivity
from app.schemas.proactive_intelligence import (
    DailyPlanOut,
    FocusOut,
    IntelligenceItemOut,
    ProjectHealthOut,
    ProactiveOverviewOut,
    ProactiveWeeklyReviewOut,
)
from app.services.goal_progress_service import COMPLETED_TASK_STATUSES, GoalProgressService
from app.services.workspace_service import WorkspaceService
from app.tasks.service import OPEN_STATUSES

PRIORITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}


@dataclass
class IntelligenceContext:
    projects: list[Project]
    goals: list[Goal]
    tasks: list[Task]
    notes: list[Note]
    memories: list[Memory]
    activities: list[WorkspaceActivity]
    now: datetime


class ProactiveIntelligenceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.workspace = WorkspaceService(session)
        self.goals = GoalProgressService(session)

    async def overview(self, user_id: UUID) -> ProactiveOverviewOut:
        context = await self._context(user_id)
        recommendations = self._recommendations(context)
        health = self._project_health(context)
        return ProactiveOverviewOut(
            daily_plan=self._daily_plan(context, recommendations),
            focus=self._focus(context, recommendations, health),
            insights=self._insights(context, health),
            project_health=health,
            recommendations=recommendations,
        )

    async def generate_daily_plan(self, user_id: UUID) -> DailyPlanOut:
        context = await self._context(user_id)
        return self._daily_plan(context, self._recommendations(context))

    async def generate_weekly_review(self, user_id: UUID) -> ProactiveWeeklyReviewOut:
        context = await self._context(user_id)
        start = context.now - timedelta(days=7)
        recent = [item for item in context.activities if self._as_utc(item.created_at) >= start]
        wins = [item.title for item in recent if item.action in {"task_completed", "milestone_completed", "goal_completed"}]
        moved_projects = list(dict.fromkeys(item.title for item in recent if item.action in {"project_updated", "note_created", "task_completed"}))
        missed = [
            task.title
            for task in context.tasks
            if task.status in OPEN_STATUSES and task.due_at and self._as_utc(task.due_at) < context.now
        ]
        missed.extend(
            project.name
            for project in context.projects
            if project.status == "active" and self._inactive_days(project.updated_at, context.now) >= 7
        )
        return ProactiveWeeklyReviewOut(
            period_start=start,
            period_end=context.now,
            wins=list(dict.fromkeys(wins)),
            progress_made=moved_projects,
            missed_objectives=list(dict.fromkeys(missed)),
            suggested_next_steps=self._recommendations(context)[:5],
        )

    async def calculate_project_health(self, user_id: UUID, project_id: UUID | None = None) -> list[ProjectHealthOut]:
        health = self._project_health(await self._context(user_id))
        return [item for item in health if project_id is None or item.project_id == project_id]

    async def generate_insights(self, user_id: UUID) -> list[IntelligenceItemOut]:
        context = await self._context(user_id)
        return self._insights(context, self._project_health(context))

    async def recommend_next_actions(self, user_id: UUID) -> list[IntelligenceItemOut]:
        return self._recommendations(await self._context(user_id))

    async def determine_focus(self, user_id: UUID) -> FocusOut:
        context = await self._context(user_id)
        recommendations = self._recommendations(context)
        return self._focus(context, recommendations, self._project_health(context))

    async def _context(self, user_id: UUID) -> IntelligenceContext:
        activity_result = await self.session.execute(
            select(WorkspaceActivity)
            .where(WorkspaceActivity.user_id == user_id)
            .order_by(WorkspaceActivity.created_at.desc())
            .limit(250)
        )
        return IntelligenceContext(
            projects=await self.workspace._projects(user_id),
            goals=await self.goals.list_goals(user_id),
            tasks=await self.workspace._tasks(user_id),
            notes=await self.workspace._notes(user_id),
            memories=await MemoryService(self.session).search_memory(user_id=user_id, limit=40),
            activities=list(activity_result.scalars()),
            now=datetime.now(timezone.utc),
        )

    def _recommendations(self, context: IntelligenceContext) -> list[IntelligenceItemOut]:
        recommendations: list[IntelligenceItemOut] = []
        for task in sorted(
            (item for item in context.tasks if item.status in OPEN_STATUSES),
            key=lambda item: (
                bool(item.due_at and self._as_utc(item.due_at) < context.now),
                PRIORITY_WEIGHT.get(item.priority, 0),
                -self._inactive_days(item.updated_at, context.now),
            ),
            reverse=True,
        ):
            overdue = bool(task.due_at and self._as_utc(task.due_at) < context.now)
            recommendations.append(
                IntelligenceItemOut(
                    type="task",
                    title=task.title,
                    detail="This is overdue and should be cleared first." if overdue else "This is an open high-impact next action.",
                    severity="attention" if overdue else "info",
                    priority="high" if overdue else task.priority,
                    project_id=task.project_id,
                    task_id=task.id,
                )
            )
        for goal in context.goals:
            if goal.status == "active" and not goal.milestones:
                recommendations.append(
                    IntelligenceItemOut(
                        type="project_improvement",
                        title=f"Break down {goal.title}",
                        detail="Add milestones so Synzept can recommend concrete next actions.",
                        goal_id=goal.id,
                    )
                )
        learning_memory = next(
            (item for item in context.memories if (item.category or item.memory_type) in {"interests", "skills"}),
            None,
        )
        if learning_memory:
            topic = learning_memory.summary or learning_memory.content
            recommendations.append(
                IntelligenceItemOut(
                    type="learning_resource",
                    title=f"Deepen {topic}",
                    detail="This remembered interest may support your active goals. Schedule a focused learning block.",
                    priority="low",
                    project_id=learning_memory.project_id,
                )
            )
        return recommendations[:12]

    def _daily_plan(self, context: IntelligenceContext, recommendations: list[IntelligenceItemOut]) -> DailyPlanOut:
        health = self._project_health(context)
        focus = self._focus(context, recommendations, health)
        areas = []
        if focus.project_title:
            areas.append(f"Move {focus.project_title} forward")
        if focus.goal_title:
            areas.append(f"Advance {focus.goal_title}")
        if any(item.severity == "attention" for item in recommendations):
            areas.append("Clear overdue work before starting new tasks")
        return DailyPlanOut(
            generated_at=context.now,
            top_priorities=recommendations[:3],
            suggested_tasks=[item for item in recommendations if item.type == "task"][:5],
            focus_areas=areas[:3],
        )

    def _focus(
        self,
        context: IntelligenceContext,
        recommendations: list[IntelligenceItemOut],
        health: list[ProjectHealthOut],
    ) -> FocusOut:
        highest = recommendations[0] if recommendations else None
        project_id = highest.project_id if highest else None
        focused_health = next((item for item in health if item.project_id == project_id), None)
        if not focused_health and health:
            focused_health = max(health, key=lambda item: (item.completion_score, item.momentum_score))
            project_id = focused_health.project_id
        goal = next(
            (
                item
                for item in context.goals
                if item.status == "active" and (project_id is None or item.project_id == project_id)
            ),
            next((item for item in context.goals if item.status == "active"), None),
        )
        active_projects = sum(item.status == "active" for item in context.projects)
        active_goals = sum(item.status == "active" for item in context.goals)
        warning = None
        if active_projects > 3 or active_goals > 4:
            warning = f"Attention is split across {active_projects} active projects and {active_goals} active goals."
        return FocusOut(
            project_id=project_id,
            project_title=focused_health.project_title if focused_health else None,
            goal_id=goal.id if goal else None,
            goal_title=goal.title if goal else None,
            highest_impact_action=highest,
            attention_warning=warning,
        )

    def _insights(self, context: IntelligenceContext, health: list[ProjectHealthOut]) -> list[IntelligenceItemOut]:
        insights: list[IntelligenceItemOut] = []
        for project in context.projects:
            days = self._inactive_days(project.updated_at, context.now)
            if project.status == "active" and days >= 7:
                insights.append(IntelligenceItemOut(type="stalled_project", title=project.name, detail=f"This project has not been updated in {days} days.", severity="attention", priority="high", project_id=project.id))
        for task in context.tasks:
            if task.status in OPEN_STATUSES and task.due_at and self._as_utc(task.due_at) < context.now:
                insights.append(IntelligenceItemOut(type="missed_objective", title=task.title, detail="This task is overdue.", severity="attention", priority="high", project_id=task.project_id, task_id=task.id))
            elif task.status in OPEN_STATUSES and self._inactive_days(task.updated_at, context.now) >= 7:
                insights.append(IntelligenceItemOut(type="inactive_work", title=task.title, detail="This open task has not moved for 7 days.", severity="attention", project_id=task.project_id, task_id=task.id))
        for goal in context.goals:
            if goal.status == "active" and goal.progress == 0 and self._inactive_days(goal.updated_at, context.now) >= 7:
                insights.append(IntelligenceItemOut(type="missed_goal", title=goal.title, detail="This active goal has not recorded progress for 7 days.", severity="attention", goal_id=goal.id, project_id=goal.project_id))
            for milestone in goal.milestones:
                if milestone.status != "completed":
                    insights.append(IntelligenceItemOut(type="unfinished_milestone", title=milestone.title, detail=f"{round(milestone.progress)}% complete in {goal.title}.", goal_id=goal.id, milestone_id=milestone.id, project_id=goal.project_id))
        updates = Counter(item.task_id for item in context.activities if item.task_id and item.action == "task_updated")
        for task_id, count in updates.items():
            if count >= 2:
                task = next((item for item in context.tasks if item.id == task_id and item.status in OPEN_STATUSES), None)
                if task:
                    insights.append(IntelligenceItemOut(type="repeated_blocker", title=task.title, detail=f"This open task has been revisited {count} times without completion.", severity="attention", priority="high", project_id=task.project_id, task_id=task.id))
        for note in context.notes:
            text = f"{note.title or ''} {note.summary or ''} {note.content}".lower()
            if "blocked" in text or "blocker" in text:
                insights.append(IntelligenceItemOut(type="blocker_note", title=note.title or "Recorded blocker", detail="A workspace note mentions a blocker that may need resolution.", severity="attention", project_id=note.project_id, goal_id=note.goal_id))
        if health:
            closest = max(health, key=lambda item: item.completion_score)
            insights.append(IntelligenceItemOut(type="closest_project", title=closest.project_title, detail=f"This project is closest to completion at {round(closest.completion_score)}%.", project_id=closest.project_id))
        return insights[:16]

    def _project_health(self, context: IntelligenceContext) -> list[ProjectHealthOut]:
        result = []
        for project in context.projects:
            tasks = [item for item in context.tasks if item.project_id == project.id]
            goals = [item for item in context.goals if item.project_id == project.id]
            completion = self.workspace._project_progress(project.id, context.goals, context.tasks)
            inactive_days = self._inactive_days(project.updated_at, context.now)
            overdue = sum(
                bool(item.status in OPEN_STATUSES and item.due_at and self._as_utc(item.due_at) < context.now)
                for item in tasks
            )
            recent_completions = sum(
                item.status in COMPLETED_TASK_STATUSES and self._as_utc(item.updated_at) >= context.now - timedelta(days=7)
                for item in tasks
            )
            momentum = self._clamp(100 - inactive_days * 8 + recent_completions * 10)
            risk = self._clamp(overdue * 22 + max(0, inactive_days - 3) * 7 + (12 if goals and completion == 0 else 0))
            health_score = round(momentum * 0.45 + completion * 0.35 + (100 - risk) * 0.20, 2)
            reasons = []
            if recent_completions:
                reasons.append(f"{recent_completions} task completion(s) recorded this week.")
            if inactive_days >= 7:
                reasons.append(f"No project update for {inactive_days} days.")
            if overdue:
                reasons.append(f"{overdue} overdue task(s) need attention.")
            if not reasons:
                reasons.append("No immediate risk signals detected.")
            result.append(ProjectHealthOut(project_id=project.id, project_title=project.name, health_score=health_score, momentum_score=momentum, completion_score=completion, risk_score=risk, reasons=reasons))
        return sorted(result, key=lambda item: item.health_score, reverse=True)

    @staticmethod
    def _inactive_days(value: datetime, now: datetime) -> int:
        return max(0, (now - ProactiveIntelligenceService._as_utc(value)).days)

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(100.0, float(value))), 2)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
