from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.goal import Goal, Milestone
from app.models.project import Project
from app.models.task import Task
from app.schemas.goal import (
    GoalCreate,
    GoalDashboardOut,
    GoalUpdate,
    MilestoneCreate,
    MilestoneUpdate,
    NextActionOut,
    WeeklyReviewOut,
)
from app.schemas.task import TaskCreate
from app.tasks.service import OPEN_STATUSES, TaskService
from app.services.workspace_activity_service import WorkspaceActivityService

COMPLETED_TASK_STATUSES = {"completed", "done"}
PRIORITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}


class GoalProgressService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.activity = WorkspaceActivityService(session)

    async def list_goals(self, user_id: UUID, *, status: str | None = None) -> list[Goal]:
        statement = (
            select(Goal)
            .options(selectinload(Goal.milestones).selectinload(Milestone.tasks))
            .where(Goal.user_id == user_id, Goal.deleted_at.is_(None))
            .execution_options(populate_existing=True)
        )
        if status:
            statement = statement.where(Goal.status == status)
        result = await self.session.execute(statement.order_by(Goal.created_at.desc()))
        return list(result.scalars().unique().all())

    async def get_goal(self, user_id: UUID, goal_id: UUID) -> Goal:
        result = await self.session.execute(
            select(Goal)
            .options(selectinload(Goal.milestones).selectinload(Milestone.tasks))
            .where(Goal.id == goal_id, Goal.user_id == user_id, Goal.deleted_at.is_(None))
            .execution_options(populate_existing=True)
        )
        goal = result.scalar_one_or_none()
        if not goal:
            raise NotFoundError("Goal not found")
        return goal

    async def create_goal(self, user_id: UUID, data: GoalCreate) -> Goal:
        if data.project_id:
            await self._owned_project(user_id, data.project_id)
        goal = Goal(user_id=user_id, **data.model_dump())
        self.session.add(goal)
        await self.session.flush()
        await self.activity.record(user_id=user_id, action="goal_created", title=goal.title, project_id=goal.project_id, goal_id=goal.id)
        return await self.get_goal(user_id, goal.id)

    async def update_goal(self, user_id: UUID, goal_id: UUID, data: GoalUpdate) -> Goal:
        goal = await self.get_goal(user_id, goal_id)
        values = data.model_dump(exclude_unset=True)
        if values.get("project_id"):
            await self._owned_project(user_id, values["project_id"])
        for field, value in values.items():
            setattr(goal, field, value)
        await self.session.flush()
        await self.activity.record(user_id=user_id, action="goal_updated", title=goal.title, project_id=goal.project_id, goal_id=goal.id)
        return await self.get_goal(user_id, goal.id)

    async def delete_goal(self, user_id: UUID, goal_id: UUID) -> None:
        goal = await self.get_goal(user_id, goal_id)
        goal.deleted_at = datetime.now(timezone.utc)
        await self.activity.record(user_id=user_id, action="goal_deleted", title=goal.title, project_id=goal.project_id, goal_id=goal.id)

    async def create_milestone(self, user_id: UUID, goal_id: UUID, data: MilestoneCreate) -> Goal:
        goal = await self.get_goal(user_id, goal_id)
        position = data.position if data.position is not None else len(goal.milestones)
        milestone = Milestone(
                goal_id=goal.id,
                title=data.title,
                description=data.description,
                position=position,
            )
        self.session.add(milestone)
        await self.session.flush()
        await self.activity.record(user_id=user_id, action="milestone_created", title=milestone.title, project_id=goal.project_id, goal_id=goal.id)
        return await self.recalculate_goal(goal.id, user_id=user_id)

    async def update_milestone(
        self,
        user_id: UUID,
        goal_id: UUID,
        milestone_id: UUID,
        data: MilestoneUpdate,
    ) -> Goal:
        milestone = await self._owned_milestone(user_id, goal_id, milestone_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(milestone, field, value)
        await self.session.flush()
        goal = await self.get_goal(user_id, goal_id)
        await self.activity.record(user_id=user_id, action="milestone_updated", title=milestone.title, project_id=goal.project_id, goal_id=goal.id)
        return await self.recalculate_goal(goal_id, user_id=user_id)

    async def create_task(self, user_id: UUID, goal_id: UUID, milestone_id: UUID, data: TaskCreate) -> Goal:
        milestone = await self._owned_milestone(user_id, goal_id, milestone_id)
        goal = await self.get_goal(user_id, goal_id)
        payload = data.model_copy(
            update={
                "milestone_id": milestone.id,
                "project_id": data.project_id or goal.project_id,
            }
        )
        await TaskService(self.session).create(user_id, payload)
        return await self.recalculate_goal(goal_id, user_id=user_id)

    async def recalculate_goal(self, goal_id: UUID, *, user_id: UUID | None = None) -> Goal:
        statement = (
            select(Goal)
            .options(selectinload(Goal.milestones).selectinload(Milestone.tasks))
            .where(Goal.id == goal_id, Goal.deleted_at.is_(None))
            .execution_options(populate_existing=True)
        )
        if user_id:
            statement = statement.where(Goal.user_id == user_id)
        result = await self.session.execute(statement)
        goal = result.scalar_one_or_none()
        if not goal:
            raise NotFoundError("Goal not found")

        milestones = [item for item in goal.milestones if item.deleted_at is None]
        previous_goal_status = goal.status
        previous_milestone_statuses = {item.id: item.status for item in milestones}
        for milestone in milestones:
            tasks = [task for task in milestone.tasks if task.deleted_at is None]
            completed = sum(task.status in COMPLETED_TASK_STATUSES for task in tasks)
            milestone.progress = round(completed / len(tasks) * 100, 2) if tasks else (100.0 if milestone.status == "completed" else 0.0)
            if tasks:
                milestone.status = (
                    "completed"
                    if completed == len(tasks)
                    else "in_progress"
                    if completed
                    else "pending"
                )

        completed_milestones = sum(item.status == "completed" for item in milestones)
        goal.progress = round(completed_milestones / len(milestones) * 100, 2) if milestones else 0.0
        if milestones and completed_milestones == len(milestones):
            goal.status = "completed"
        elif goal.status == "completed":
            goal.status = "active"
        await self.session.flush()
        for milestone in milestones:
            if previous_milestone_statuses[milestone.id] != "completed" and milestone.status == "completed":
                await self.activity.record(
                    user_id=goal.user_id,
                    action="milestone_completed",
                    title=milestone.title,
                    project_id=goal.project_id,
                    goal_id=goal.id,
                )
        if previous_goal_status != "completed" and goal.status == "completed":
            await self.activity.record(
                user_id=goal.user_id,
                action="goal_completed",
                title=goal.title,
                project_id=goal.project_id,
                goal_id=goal.id,
            )
        return goal

    async def next_actions(self, user_id: UUID, *, limit: int = 5) -> list[NextActionOut]:
        goals = await self.list_goals(user_id, status="active")
        actions: list[NextActionOut] = []
        for goal in goals:
            milestones = sorted(
                (item for item in goal.milestones if item.deleted_at is None and item.status != "completed"),
                key=lambda item: item.position,
            )
            if not milestones:
                actions.append(
                    NextActionOut(
                        goal_id=goal.id,
                        goal_title=goal.title,
                        title=f"Define the next milestone for {goal.title}",
                        reason="This active goal needs a concrete checkpoint.",
                    )
                )
                continue
            milestone = milestones[0]
            tasks = sorted(
                (
                    task
                    for task in milestone.tasks
                    if task.deleted_at is None and task.status in OPEN_STATUSES
                ),
                key=lambda task: (-PRIORITY_WEIGHT.get(task.priority, 0), task.created_at),
            )
            if tasks:
                for task in tasks:
                    actions.append(
                        NextActionOut(
                            task_id=task.id,
                            milestone_id=milestone.id,
                            goal_id=goal.id,
                            goal_title=goal.title,
                            milestone_title=milestone.title,
                            title=task.title,
                            reason=f"Moves {milestone.title} forward.",
                            priority=task.priority,
                        )
                    )
                    if len(actions) >= limit:
                        return actions
            else:
                actions.append(
                    NextActionOut(
                        milestone_id=milestone.id,
                        goal_id=goal.id,
                        goal_title=goal.title,
                        milestone_title=milestone.title,
                        title=f"Define the next task for {milestone.title}",
                        reason="This milestone has no unfinished tasks.",
                    )
                )
            if len(actions) >= limit:
                break
        return actions[:limit]

    async def weekly_review(self, user_id: UUID) -> WeeklyReviewOut:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=7)
        result = await self.session.execute(
            select(Task)
            .where(Task.user_id == user_id, Task.deleted_at.is_(None), Task.updated_at >= start)
            .order_by(Task.updated_at.desc())
        )
        tasks = list(result.scalars())
        completed = [task.title for task in tasks if task.status in COMPLETED_TASK_STATUSES]
        blocked = [task.title for task in tasks if task.status in OPEN_STATUSES and task.priority == "high"]
        return WeeklyReviewOut(
            period_start=start,
            period_end=end,
            completed=completed,
            blocked=blocked,
            next_actions=await self.next_actions(user_id, limit=5),
        )

    async def dashboard(self, user_id: UUID) -> GoalDashboardOut:
        goals = await self.list_goals(user_id, status="active")
        project_result = await self.session.execute(
            select(Project)
            .where(Project.user_id == user_id, Project.deleted_at.is_(None), Project.status == "active")
            .order_by(Project.updated_at.desc())
            .limit(8)
        )
        tasks = await TaskService(self.session).get_priorities(user_id, limit=8)
        return GoalDashboardOut(
            active_goals=goals,
            active_projects=[project.name for project in project_result.scalars()],
            upcoming_tasks=tasks,
            recommendations=await self.next_actions(user_id, limit=5),
        )

    async def _owned_project(self, user_id: UUID, project_id: UUID) -> Project:
        result = await self.session.execute(
            select(Project).where(Project.id == project_id, Project.user_id == user_id, Project.deleted_at.is_(None))
        )
        project = result.scalar_one_or_none()
        if not project:
            raise NotFoundError("Project not found")
        return project

    async def _owned_milestone(self, user_id: UUID, goal_id: UUID, milestone_id: UUID) -> Milestone:
        result = await self.session.execute(
            select(Milestone)
            .join(Goal, Goal.id == Milestone.goal_id)
            .where(
                Milestone.id == milestone_id,
                Milestone.goal_id == goal_id,
                Milestone.deleted_at.is_(None),
                Goal.user_id == user_id,
                Goal.deleted_at.is_(None),
            )
        )
        milestone = result.scalar_one_or_none()
        if not milestone:
            raise NotFoundError("Milestone not found")
        return milestone
