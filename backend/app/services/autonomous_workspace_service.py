from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.autonomous_workspace import AutonomousSuggestion, ExecutionPlan
from app.models.goal import Goal
from app.models.project_intelligence_phase2 import OpenLoop
from app.models.task import Task
from app.schemas.autonomous_workspace import (
    AutonomousSuggestionOut,
    AutonomousWorkspaceOut,
    ExecutionPlanOut,
    ExecutionStateOut,
    GoalPlanOut,
    GoalProgressEstimateOut,
    WeeklyPlanOut,
)
from app.schemas.goal import MilestoneCreate
from app.schemas.proactive_intelligence import IntelligenceItemOut
from app.schemas.task import TaskCreate
from app.services.goal_progress_service import GoalProgressService
from app.services.proactive_intelligence_service import ProactiveIntelligenceService
from app.services.workspace_activity_service import WorkspaceActivityService
from app.tasks.service import OPEN_STATUSES


class AutonomousWorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.goals = GoalProgressService(session)
        self.activity = WorkspaceActivityService(session)

    async def overview(self, user_id: UUID) -> AutonomousWorkspaceOut:
        plans = await self._plans(user_id)
        proactive = ProactiveIntelligenceService(self.session)
        suggestions = await self.generate_suggestions(user_id)
        return AutonomousWorkspaceOut(
            plans=[self._plan_out(plan) for plan in plans],
            project_health=await proactive.calculate_project_health(user_id),
            execution=await self.execution_state(user_id),
            weekly_plan=await self.weekly_plan(user_id),
            suggestions=suggestions,
        )

    async def goal_to_plan(self, user_id: UUID, goal_id: UUID, *, create_structure: bool = True) -> GoalPlanOut:
        goal = await self.goals.get_goal(user_id, goal_id)
        blueprint = self._blueprint(goal.title)
        milestones_created = 0
        tasks_created = 0
        open_loops_created = 0
        if create_structure and not goal.milestones:
            for index, milestone in enumerate(blueprint["milestones"]):
                goal = await self.goals.create_milestone(user_id, goal.id, MilestoneCreate(title=milestone["title"], description=milestone["description"], position=index))
                milestones_created += 1
            for milestone, actions in zip(goal.milestones, blueprint["actions"]):
                for action in actions:
                    goal = await self.goals.create_task(user_id, goal.id, milestone.id, TaskCreate(title=action, project_id=goal.project_id, priority="high" if "customer" in action.casefold() else "medium"))
                    tasks_created += 1
        if create_structure and goal.project_id:
            existing = await self.session.execute(select(OpenLoop).where(OpenLoop.project_id == goal.project_id, OpenLoop.title.in_(blueprint["open_loops"])))
            existing_titles = {item.title for item in existing.scalars()}
            for title in blueprint["open_loops"]:
                if title in existing_titles:
                    continue
                self.session.add(OpenLoop(project_id=goal.project_id, title=title, description=f"Generated from goal: {goal.title}", status="open"))
                open_loops_created += 1
        await self.session.flush()
        goal = await self.goals.recalculate_goal(goal.id, user_id=user_id)
        plan = await self._upsert_plan(user_id, goal, blueprint)
        await self.activity.record(
            user_id=user_id,
            action="execution_plan_generated",
            title=f"Execution plan generated for {goal.title}",
            detail=f"{milestones_created} milestones, {tasks_created} tasks, and {open_loops_created} open loops were created.",
            project_id=goal.project_id,
            goal_id=goal.id,
        )
        actions = [
            IntelligenceItemOut(type="suggested_action", title=action, detail=f"Moves {goal.title} forward.", priority="high" if index == 0 else "medium", project_id=goal.project_id, goal_id=goal.id)
            for index, action in enumerate(sum(blueprint["actions"], [])[:6])
        ]
        return GoalPlanOut(goal=goal, execution_plan=self._plan_out(plan), milestones_created=milestones_created, tasks_created=tasks_created, open_loops_created=open_loops_created, suggested_actions=actions)

    async def execution_state(self, user_id: UUID) -> ExecutionStateOut:
        tasks = list((await self.session.execute(select(Task).where(Task.user_id == user_id, Task.deleted_at.is_(None)).order_by(Task.updated_at.desc()).limit(120))).scalars())
        planned = [{"id": str(task.id), "title": task.title, "project_id": str(task.project_id) if task.project_id else None, "status": task.status} for task in tasks if task.status in OPEN_STATUSES]
        completed = [{"id": str(task.id), "title": task.title, "project_id": str(task.project_id) if task.project_id else None, "status": task.status} for task in tasks if task.status in {"completed", "done"}]
        blocked = [{"id": str(task.id), "title": task.title, "project_id": str(task.project_id) if task.project_id else None, "status": task.status} for task in tasks if task.priority == "high" and task.status in OPEN_STATUSES]
        return ExecutionStateOut(planned=planned[:20], completed=completed[:20], blocked=blocked[:12])

    async def goal_progress_estimate(self, user_id: UUID, goal_id: UUID) -> GoalProgressEstimateOut:
        goal = await self.goals.get_goal(user_id, goal_id)
        remaining = [milestone.title for milestone in goal.milestones if milestone.status != "completed"]
        days = max(7, len(remaining) * 7) if remaining else 0
        return GoalProgressEstimateOut(goal_id=goal.id, current_progress=goal.progress, remaining_work=remaining, estimated_completion_days=days, estimated_completion_label="Complete" if not remaining else f"About {days} days at current structure.")

    async def weekly_plan(self, user_id: UUID) -> WeeklyPlanOut:
        next_actions = await self.goals.next_actions(user_id, limit=8)
        this_week = [IntelligenceItemOut(type="this_week", title=item.title, detail=item.reason, priority=item.priority, goal_id=item.goal_id, task_id=item.task_id, milestone_id=item.milestone_id) for item in next_actions[:4]]
        next_week = [IntelligenceItemOut(type="next_week", title=item.title, detail=item.reason, priority=item.priority, goal_id=item.goal_id, task_id=item.task_id, milestone_id=item.milestone_id) for item in next_actions[4:8]]
        focus = this_week[0].title if this_week else "Create one goal plan to generate weekly focus."
        return WeeklyPlanOut(generated_at=datetime.now(timezone.utc), this_week=this_week, next_week=next_week, priority_focus=focus)

    async def generate_suggestions(self, user_id: UUID) -> list[AutonomousSuggestionOut]:
        proactive = await ProactiveIntelligenceService(self.session).chief_of_staff(user_id, persist=False)
        generated = []
        for item in [*proactive.strategic_suggestions, *proactive.opportunities, *proactive.risks][:10]:
            generated.append(await self._upsert_suggestion(user_id, item))
        return [self._suggestion_out(item) for item in generated]

    async def _upsert_plan(self, user_id: UUID, goal: Goal, blueprint: dict) -> ExecutionPlan:
        state = await self.execution_state(user_id)
        metrics = {"progress": goal.progress, "remainingMilestones": sum(m.status != "completed" for m in goal.milestones), "estimatedCompletionDays": max(7, sum(m.status != "completed" for m in goal.milestones) * 7)}
        plan = ExecutionPlan(user_id=user_id, goal_id=goal.id, project_id=goal.project_id, status="active", plan=blueprint, planned=state.planned, completed=state.completed, blocked=state.blocked, metrics=metrics)
        try:
            async with self.session.begin_nested():
                self.session.add(plan)
                await self.session.flush()
                return plan
        except IntegrityError:
            existing = (await self.session.execute(select(ExecutionPlan).where(ExecutionPlan.user_id == user_id, ExecutionPlan.goal_id == goal.id))).scalar_one()
            existing.plan = blueprint
            existing.planned = state.planned
            existing.completed = state.completed
            existing.blocked = state.blocked
            existing.metrics = metrics
            existing.updated_at = datetime.now(timezone.utc)
            await self.session.flush()
            return existing

    async def _upsert_suggestion(self, user_id: UUID, item: IntelligenceItemOut) -> AutonomousSuggestion:
        existing = (await self.session.execute(select(AutonomousSuggestion).where(AutonomousSuggestion.user_id == user_id, AutonomousSuggestion.title == item.title, AutonomousSuggestion.status == "pending").limit(1))).scalar_one_or_none()
        if existing:
            existing.detail = item.detail
            existing.priority = item.priority
            existing.updated_at = datetime.now(timezone.utc)
            return existing
        suggestion = AutonomousSuggestion(user_id=user_id, project_id=item.project_id, goal_id=item.goal_id, suggestion_type=item.type, title=item.title, detail=item.detail, priority=item.priority, evidence={"severity": item.severity})
        self.session.add(suggestion)
        await self.session.flush()
        await self.activity.record(user_id=user_id, action="autonomous_suggestion_created", title=suggestion.title, detail=suggestion.detail, project_id=suggestion.project_id, goal_id=suggestion.goal_id)
        return suggestion

    async def _plans(self, user_id: UUID) -> list[ExecutionPlan]:
        return list((await self.session.execute(select(ExecutionPlan).where(ExecutionPlan.user_id == user_id).order_by(ExecutionPlan.updated_at.desc()).limit(20))).scalars())

    @staticmethod
    def _blueprint(goal_title: str) -> dict:
        lower = goal_title.casefold()
        if "paying user" in lower or "customer" in lower or "growth" in lower:
            milestones = [
                {"title": "Define the customer segment", "description": "Clarify who should pay first and why."},
                {"title": "Create acquisition motion", "description": "Build outreach, onboarding, and conversion loops."},
                {"title": "Convert and retain early users", "description": "Track activation, payment, and retention signals."},
            ]
            actions = [["Identify 20 target customers", "Write the core offer"], ["Ship onboarding path", "Run weekly customer outreach"], ["Follow up with trial users", "Review conversion blockers"]]
            open_loops = ["Customer acquisition", "Onboarding conversion", "Retention feedback"]
        else:
            milestones = [{"title": "Clarify outcome", "description": "Define success and constraints."}, {"title": "Build execution path", "description": "Create the work sequence."}, {"title": "Review and complete", "description": "Close blockers and confirm progress."}]
            actions = [["Define success criteria", "Choose the first project anchor"], ["Create first deliverable", "Review blockers"], ["Complete remaining work", "Record outcome"]]
            open_loops = ["Clarify next action", "Resolve blockers", "Confirm outcome"]
        return {"milestones": milestones, "actions": actions, "open_loops": open_loops}

    @staticmethod
    def _plan_out(plan: ExecutionPlan) -> ExecutionPlanOut:
        return ExecutionPlanOut(id=plan.id, goal_id=plan.goal_id, project_id=plan.project_id, status=plan.status, plan=plan.plan or {}, planned=plan.planned or [], completed=plan.completed or [], blocked=plan.blocked or [], metrics=plan.metrics or {}, created_at=plan.created_at, updated_at=plan.updated_at)

    @staticmethod
    def _suggestion_out(item: AutonomousSuggestion) -> AutonomousSuggestionOut:
        return AutonomousSuggestionOut(id=item.id, suggestion_type=item.suggestion_type, title=item.title, detail=item.detail or "", priority=item.priority, status=item.status, project_id=item.project_id, goal_id=item.goal_id, evidence=item.evidence or {}, created_at=item.created_at, updated_at=item.updated_at)
