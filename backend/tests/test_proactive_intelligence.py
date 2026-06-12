from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database.base import Base
from app.models.user import User
from app.schemas.goal import GoalCreate, MilestoneCreate
from app.schemas.project import ProjectCreate
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.goal_progress_service import GoalProgressService
from app.services.proactive_intelligence_service import ProactiveIntelligenceService
from app.services.workspace_service import WorkspaceService
from app.tasks.service import TaskService


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'proactive.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_proactive_engine_detects_risk_blockers_and_focus(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        session.add(User(id=user_id, email="proactive@example.com"))
        await session.flush()
        workspace = WorkspaceService(session)
        project = await workspace.create_project(user_id, ProjectCreate(name="Synzept"))
        raw_project = await workspace._owned_project(user_id, project.id)
        raw_project.updated_at = datetime.now(timezone.utc) - timedelta(days=10)

        goals = GoalProgressService(session)
        goal = await goals.create_goal(user_id, GoalCreate(title="Launch Synzept", project_id=project.id))
        goal = await goals.create_milestone(user_id, goal.id, MilestoneCreate(title="Build intelligence engine"))
        goal = await goals.create_task(
            user_id,
            goal.id,
            goal.milestones[0].id,
            TaskCreate(
                title="Finish recommendation rules",
                project_id=project.id,
                priority="high",
                due_at=datetime.now(timezone.utc) - timedelta(days=1),
            ),
        )
        task = goal.milestones[0].tasks[0]
        await TaskService(session).update(task.id, user_id, TaskUpdate(description="First pass"))
        await TaskService(session).update(task.id, user_id, TaskUpdate(description="Second pass"))

        service = ProactiveIntelligenceService(session)
        overview = await service.overview(user_id)
        insight_types = {item.type for item in overview.insights}

        assert {"stalled_project", "missed_objective", "unfinished_milestone", "repeated_blocker"} <= insight_types
        assert overview.daily_plan.top_priorities[0].title == "Finish recommendation rules"
        assert overview.focus.project_title == "Synzept"
        assert overview.focus.highest_impact_action.title == "Finish recommendation rules"
        assert overview.project_health[0].risk_score > 0


@pytest.mark.asyncio
async def test_weekly_review_reports_wins_and_next_steps(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        session.add(User(id=user_id, email="review@example.com"))
        await session.flush()
        workspace = WorkspaceService(session)
        project = await workspace.create_project(user_id, ProjectCreate(name="Launch plan"))
        goals = GoalProgressService(session)
        goal = await goals.create_goal(user_id, GoalCreate(title="Ship MVP", project_id=project.id))
        goal = await goals.create_milestone(user_id, goal.id, MilestoneCreate(title="Finish beta"))
        goal = await goals.create_task(user_id, goal.id, goal.milestones[0].id, TaskCreate(title="Close release checklist", project_id=project.id))
        task = goal.milestones[0].tasks[0]
        await TaskService(session).update(task.id, user_id, TaskUpdate(status="completed"))

        review = await ProactiveIntelligenceService(session).generate_weekly_review(user_id)

        assert "Close release checklist" in review.wins
        assert review.period_start < review.period_end
