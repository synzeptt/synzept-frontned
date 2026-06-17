from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.memory_service import MemoryService
from app.models.chief_of_staff import ChiefOfStaffSnapshot, Commitment
from app.models.goal import Goal
from app.models.memory import Memory
from app.models.note import Note
from app.models.project import Project
from app.models.project_intelligence_phase2 import Decision, OpenLoop
from app.models.task import Task
from app.models.user_understanding import UserUnderstanding
from app.models.workspace_activity import WorkspaceActivity
from app.schemas.proactive_intelligence import (
    ChiefOfStaffOut,
    CommitmentOut,
    DailyPlanOut,
    ExecutiveBriefOut,
    FocusOut,
    FounderReportOut,
    IntelligenceItemOut,
    MomentumScoreOut,
    ProjectHealthOut,
    ProactiveOverviewOut,
    ProactiveWeeklyReviewOut,
)
from app.services.goal_progress_service import COMPLETED_TASK_STATUSES, GoalProgressService
from app.services.relationship_graph_phase5_service import RelationshipGraphPhase5Service
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
    understanding: list[UserUnderstanding]
    decisions: list[Decision]
    open_loops: list[OpenLoop]
    commitments: list[Commitment]
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
            chief_of_staff=await self.chief_of_staff(user_id, persist=False),
        )

    async def chief_of_staff(self, user_id: UUID, *, persist: bool = True) -> ChiefOfStaffOut:
        context = await self._context(user_id)
        graph = await RelationshipGraphPhase5Service(self.session).context_for_query(user_id, self._graph_query(context), limit=14)
        recommendations = self._recommendations(context)
        health = self._project_health(context)
        risks = self._risks(context, health)
        opportunities = self._opportunities(context, graph)
        priorities = self._priority_engine(context, recommendations, risks)
        strategic = self._strategic_suggestions(context, graph, opportunities, risks)
        output = ChiefOfStaffOut(
            executive_brief=self._executive_brief(context, recommendations, risks),
            opportunities=opportunities,
            risks=risks,
            priorities=priorities,
            commitments=[self._commitment_out(item) for item in context.commitments[:10]],
            momentum=self._momentum(context),
            strategic_suggestions=strategic,
            founder_report=self._founder_report(context, strategic),
        )
        if persist:
            await self._persist_snapshot(user_id, output)
        return output

    async def founder_report(self, user_id: UUID) -> FounderReportOut:
        return (await self.chief_of_staff(user_id, persist=True)).founder_report

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
        project_rows = await self.workspace._projects(user_id)
        project_ids = [project.id for project in project_rows]
        understanding_result = await self.session.execute(
            select(UserUnderstanding).where(UserUnderstanding.user_id == user_id).order_by(UserUnderstanding.updated_at.desc()).limit(80)
        )
        commitment_result = await self.session.execute(
            select(Commitment).where(Commitment.user_id == user_id).order_by(Commitment.updated_at.desc()).limit(80)
        )
        decisions: list[Decision] = []
        open_loops: list[OpenLoop] = []
        if project_ids:
            decision_result = await self.session.execute(
                select(Decision).where(Decision.project_id.in_(project_ids)).order_by(Decision.updated_at.desc()).limit(120)
            )
            loop_result = await self.session.execute(
                select(OpenLoop).where(OpenLoop.project_id.in_(project_ids), OpenLoop.status == "open").order_by(OpenLoop.updated_at.desc()).limit(120)
            )
            decisions = list(decision_result.scalars())
            open_loops = list(loop_result.scalars())
        return IntelligenceContext(
            projects=project_rows,
            goals=await self.goals.list_goals(user_id),
            tasks=await self.workspace._tasks(user_id),
            notes=await self.workspace._notes(user_id),
            memories=await MemoryService(self.session).search_memory(user_id=user_id, limit=40),
            activities=list(activity_result.scalars()),
            understanding=list(understanding_result.scalars()),
            decisions=decisions,
            open_loops=open_loops,
            commitments=list(commitment_result.scalars()),
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

    def _executive_brief(
        self,
        context: IntelligenceContext,
        recommendations: list[IntelligenceItemOut],
        risks: list[IntelligenceItemOut],
    ) -> ExecutiveBriefOut:
        recent = [item for item in context.activities if self._as_utc(item.created_at) >= context.now - timedelta(days=3)]
        what_changed = list(dict.fromkeys([f"{item.title}: {item.action.replace('_', ' ')}" for item in recent[:8]]))
        what_matters = []
        what_matters.extend(goal.title for goal in context.goals if goal.status == "active")
        what_matters.extend(project.name for project in context.projects if project.status == "active")
        return ExecutiveBriefOut(
            generated_at=context.now,
            what_changed=what_changed[:6] or ["No major workspace changes were recorded in the last 3 days."],
            what_matters_now=list(dict.fromkeys(what_matters))[:6],
            needs_attention=risks[:5],
            recommended_next_action=recommendations[0] if recommendations else None,
        )

    def _opportunities(self, context: IntelligenceContext, graph) -> list[IntelligenceItemOut]:
        opportunities: list[IntelligenceItemOut] = []
        text = self._workspace_text(context)
        active_launch = next((project for project in context.projects if "launch" in f"{project.name} {project.description or ''}".casefold()), None)
        recent_user_activity = any("user" in item.title.casefold() or "customer" in item.title.casefold() for item in context.activities[:40])
        if active_launch and not recent_user_activity:
            opportunities.append(IntelligenceItemOut(type="opportunity", title="Talk to users this week", detail=f"You are working on {active_launch.name}, but recent activity does not show customer conversations.", priority="high", project_id=active_launch.id))
        payments_project = next((project for project in context.projects if "payment" in f"{project.name} {project.description or ''} {project.current_focus}".casefold()), None)
        promoted = any(word in text for word in ("promote", "launch post", "marketing", "distribution", "waitlist"))
        if payments_project and not promoted:
            opportunities.append(IntelligenceItemOut(type="opportunity", title="Promote what you built", detail="Payments or monetization work exists, but promotion/distribution is not visible in recent context.", priority="high", project_id=payments_project.id))
        for decision in context.decisions:
            if decision.status == "decided" and "launch" in decision.title.casefold():
                opportunities.append(IntelligenceItemOut(type="decision_leverage", title=f"Act on decision: {decision.title}", detail=decision.reason or decision.description or "This decision should produce a concrete next move.", project_id=decision.project_id))
        for item in graph.supportingContext[:3]:
            opportunities.append(IntelligenceItemOut(type="graph_opportunity", title=item.title, detail=item.reason or item.description, priority="medium"))
        return self._dedupe_items(opportunities)[:8]

    def _risks(self, context: IntelligenceContext, health: list[ProjectHealthOut]) -> list[IntelligenceItemOut]:
        risks: list[IntelligenceItemOut] = []
        primary_goal = next((goal for goal in context.goals if goal.status == "active"), None)
        if primary_goal:
            recent_goal_activity = any(item.goal_id == primary_goal.id for item in context.activities[:60])
            if not recent_goal_activity:
                risks.append(IntelligenceItemOut(type="focus_drift", title=f"Focus drift from {primary_goal.title}", detail="Recent activity does not show movement on the primary active goal.", severity="attention", priority="high", goal_id=primary_goal.id, project_id=primary_goal.project_id))
        for project in context.projects:
            days = self._inactive_days(project.updated_at, context.now)
            if project.status == "active" and days >= 14:
                risks.append(IntelligenceItemOut(type="stalled_project", title=project.name, detail=f"Important project has been inactive for {days} days.", severity="attention", priority="high", project_id=project.id))
        for loop in context.open_loops[:8]:
            risks.append(IntelligenceItemOut(type="open_loop", title=loop.title, detail=loop.description or "This unfinished loop can slow progress.", severity="attention", priority="high", project_id=loop.project_id))
        for commitment in context.commitments:
            if commitment.status == "open" and commitment.due_at and self._as_utc(commitment.due_at) < context.now:
                risks.append(IntelligenceItemOut(type="missed_commitment", title=commitment.title, detail="This commitment appears incomplete after its due date.", severity="attention", priority="high", project_id=commitment.project_id, goal_id=commitment.goal_id))
        for project_health in health:
            if project_health.risk_score >= 60:
                risks.append(IntelligenceItemOut(type="project_risk", title=project_health.project_title, detail="; ".join(project_health.reasons), severity="attention", priority="high", project_id=project_health.project_id))
        return self._dedupe_items(risks)[:12]

    def _priority_engine(
        self,
        context: IntelligenceContext,
        recommendations: list[IntelligenceItemOut],
        risks: list[IntelligenceItemOut],
    ) -> list[IntelligenceItemOut]:
        ranked: list[tuple[float, IntelligenceItemOut]] = []
        for goal in context.goals:
            if goal.status != "active":
                continue
            score = 80 - goal.progress * 0.25 + (15 if goal.target_date else 0)
            ranked.append((score, IntelligenceItemOut(type="goal_priority", title=goal.title, detail=f"{round(goal.progress)}% complete.", priority="high", goal_id=goal.id, project_id=goal.project_id)))
        for project in context.projects:
            if project.status != "active":
                continue
            days = self._inactive_days(project.updated_at, context.now)
            score = 70 + max(0, 14 - days)
            ranked.append((score, IntelligenceItemOut(type="project_priority", title=project.name, detail=project.recommended_next_step or project.current_focus or "Choose the next concrete move.", project_id=project.id)))
        for loop in context.open_loops:
            ranked.append((92, IntelligenceItemOut(type="open_loop_priority", title=loop.title, detail=loop.description or "Close this loop before adding new work.", severity="attention", priority="high", project_id=loop.project_id)))
        for item in recommendations[:6]:
            ranked.append((75 + PRIORITY_WEIGHT.get(item.priority, 1), item))
        for item in risks[:6]:
            ranked.append((95, item))
        return [item for _, item in sorted(ranked, key=lambda entry: entry[0], reverse=True)][:10]

    def _momentum(self, context: IntelligenceContext) -> MomentumScoreOut:
        now = context.now
        last_7 = [item for item in context.activities if self._as_utc(item.created_at) >= now - timedelta(days=7)]
        prev_7 = [item for item in context.activities if now - timedelta(days=14) <= self._as_utc(item.created_at) < now - timedelta(days=7)]
        active_days = len({self._as_utc(item.created_at).date() for item in last_7})
        completions = sum(item.action in {"task_completed", "milestone_completed", "goal_completed"} for item in last_7)
        activity_score = self._clamp(len(last_7) * 6)
        progress_score = self._clamp(completions * 25)
        consistency_score = self._clamp(active_days / 7 * 100)
        score = round(activity_score * 0.35 + progress_score * 0.4 + consistency_score * 0.25, 2)
        previous = len(prev_7)
        trend = "up" if len(last_7) > previous else "down" if len(last_7) < previous else "flat"
        return MomentumScoreOut(score=score, trend=trend, activity_score=activity_score, progress_score=progress_score, consistency_score=consistency_score, explanation=f"{len(last_7)} activity item(s), {completions} completion(s), {active_days} active day(s) in the last week.")

    def _strategic_suggestions(self, context: IntelligenceContext, graph, opportunities: list[IntelligenceItemOut], risks: list[IntelligenceItemOut]) -> list[IntelligenceItemOut]:
        suggestions: list[IntelligenceItemOut] = []
        if risks:
            risk = risks[0]
            suggestions.append(IntelligenceItemOut(type="strategic_action", title=f"Resolve {risk.title}", detail=f"This is the highest-risk item surfaced by Chief of Staff: {risk.detail}", severity=risk.severity, priority="high", project_id=risk.project_id, goal_id=risk.goal_id))
        if opportunities:
            opportunity = opportunities[0]
            suggestions.append(IntelligenceItemOut(type="strategic_action", title=opportunity.title, detail=opportunity.detail, priority=opportunity.priority, project_id=opportunity.project_id))
        launch_decision = next((decision for decision in context.decisions if "launch" in decision.title.casefold()), None)
        if launch_decision:
            suggestions.append(IntelligenceItemOut(type="strategic_action", title="Turn launch decision into distribution work", detail=launch_decision.reason or "A launch decision should create customer-facing action.", priority="high", project_id=launch_decision.project_id))
        if graph.nextActions:
            action = graph.nextActions[0]
            suggestions.append(IntelligenceItemOut(type="graph_next_action", title=action.title, detail=action.reason or action.description, priority="medium"))
        return self._dedupe_items(suggestions)[:8]

    def _founder_report(self, context: IntelligenceContext, recommendations: list[IntelligenceItemOut]) -> FounderReportOut:
        start = context.now - timedelta(days=7)
        recent = [item for item in context.activities if self._as_utc(item.created_at) >= start]
        text = self._workspace_text(context)
        return FounderReportOut(
            period_start=start,
            period_end=context.now,
            growth=[item.title for item in recent if self._contains(item.title, "growth", "marketing", "launch", "waitlist")][:6],
            revenue=[item.title for item in recent if self._contains(item.title, "revenue", "payment", "billing", "pricing")][:6],
            customers=[item.title for item in recent if self._contains(item.title, "customer", "user", "founder", "interview")][:6],
            retention=[item.title for item in recent if self._contains(item.title, "retention", "return", "activation", "habit")][:6],
            product_progress=[item.title for item in recent if item.action in {"project_updated", "task_completed", "note_created"}][:8],
            recommendations=[
                *recommendations[:4],
                *(
                    [IntelligenceItemOut(type="founder_mode", title="Create a weekly customer contact target", detail="Founder Mode sees product progress, but customer/revenue signals need explicit weekly movement.", priority="high")]
                    if not any(word in text for word in ("customer", "user interview", "revenue", "paying"))
                    else []
                ),
            ][:6],
        )

    async def _persist_snapshot(self, user_id: UUID, output: ChiefOfStaffOut) -> None:
        payload = {
            "what_changed": output.executive_brief.what_changed,
            "what_matters_now": output.executive_brief.what_matters_now,
            "needs_attention": [item.model_dump(mode="json") for item in output.executive_brief.needs_attention],
            "recommended_next_action": output.executive_brief.recommended_next_action.model_dump(mode="json") if output.executive_brief.recommended_next_action else None,
        }
        snapshot = ChiefOfStaffSnapshot(
            user_id=user_id,
            snapshot_date=date.today(),
            snapshot_type="daily",
            executive_brief=payload,
            opportunities=[item.model_dump(mode="json") for item in output.opportunities],
            risks=[item.model_dump(mode="json") for item in output.risks],
            priorities=[item.model_dump(mode="json") for item in output.priorities],
            strategic_suggestions=[item.model_dump(mode="json") for item in output.strategic_suggestions],
            momentum=output.momentum.model_dump(mode="json"),
            founder_report=output.founder_report.model_dump(mode="json") if output.founder_report else {},
        )
        try:
            async with self.session.begin_nested():
                self.session.add(snapshot)
                await self.session.flush()
        except IntegrityError:
            existing_result = await self.session.execute(
                select(ChiefOfStaffSnapshot).where(
                    ChiefOfStaffSnapshot.user_id == user_id,
                    ChiefOfStaffSnapshot.snapshot_date == date.today(),
                    ChiefOfStaffSnapshot.snapshot_type == "daily",
                )
            )
            existing = existing_result.scalar_one_or_none()
            if existing:
                existing.executive_brief = snapshot.executive_brief
                existing.opportunities = snapshot.opportunities
                existing.risks = snapshot.risks
                existing.priorities = snapshot.priorities
                existing.strategic_suggestions = snapshot.strategic_suggestions
                existing.momentum = snapshot.momentum
                existing.founder_report = snapshot.founder_report
                existing.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def _commitment_out(item: Commitment) -> CommitmentOut:
        return CommitmentOut(id=item.id, title=item.title, detail=item.detail or "", status=item.status, due_at=item.due_at, project_id=item.project_id, goal_id=item.goal_id, created_at=item.created_at, updated_at=item.updated_at)

    @staticmethod
    def _graph_query(context: IntelligenceContext) -> str:
        parts = [goal.title for goal in context.goals if goal.status == "active"]
        parts.extend(project.name for project in context.projects if project.status == "active")
        parts.extend(loop.title for loop in context.open_loops[:6])
        return " ".join(parts) or "What should I work on next?"

    @staticmethod
    def _workspace_text(context: IntelligenceContext) -> str:
        values = []
        values.extend(project.name + " " + (project.description or "") + " " + project.current_focus for project in context.projects)
        values.extend(goal.title + " " + goal.description for goal in context.goals)
        values.extend(memory.summary or memory.content for memory in context.memories)
        values.extend(item.title + " " + item.detail for item in context.activities[:80])
        return " ".join(values).casefold()

    @staticmethod
    def _contains(value: str, *needles: str) -> bool:
        text = value.casefold()
        return any(needle in text for needle in needles)

    @staticmethod
    def _dedupe_items(items: list[IntelligenceItemOut]) -> list[IntelligenceItemOut]:
        seen: set[str] = set()
        result: list[IntelligenceItemOut] = []
        for item in items:
            key = f"{item.type}:{item.title}".casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    @staticmethod
    def _inactive_days(value: datetime, now: datetime) -> int:
        return max(0, (now - ProactiveIntelligenceService._as_utc(value)).days)

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(100.0, float(value))), 2)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
