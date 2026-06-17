from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database.base import Base
from app.models.user import User
from app.schemas.goal import GoalCreate
from app.schemas.project import ProjectCreate
from app.services.autonomous_workspace_service import AutonomousWorkspaceService
from app.services.goal_progress_service import GoalProgressService
from app.services.workspace_service import WorkspaceService


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'autonomous-workspace.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_goal_to_plan_creates_execution_structure(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        session.add(User(id=user_id, email="autonomous@example.com"))
        await session.flush()
        project = await WorkspaceService(session).create_project(user_id, ProjectCreate(name="Synzept"))
        goal = await GoalProgressService(session).create_goal(
            user_id,
            GoalCreate(title="Get 100 paying users", project_id=project.id),
        )

        plan = await AutonomousWorkspaceService(session).goal_to_plan(user_id, goal.id)

        assert plan.goal.title == "Get 100 paying users"
        assert plan.milestones_created == 3
        assert plan.tasks_created == 6
        assert plan.open_loops_created == 3
        assert plan.execution_plan.status == "active"
        assert plan.execution_plan.metrics["remainingMilestones"] == 3
        assert plan.suggested_actions[0].title == "Identify 20 target customers"


@pytest.mark.asyncio
async def test_autonomous_workspace_overview_returns_execution_health_and_suggestions(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        session.add(User(id=user_id, email="overview-autonomous@example.com"))
        await session.flush()
        project = await WorkspaceService(session).create_project(user_id, ProjectCreate(name="Founder Dashboard"))
        goal = await GoalProgressService(session).create_goal(
            user_id,
            GoalCreate(title="Reach 100 paying users", project_id=project.id),
        )
        service = AutonomousWorkspaceService(session)
        await service.goal_to_plan(user_id, goal.id)

        overview = await service.overview(user_id)
        progress = await service.goal_progress_estimate(user_id, goal.id)

        assert overview.plans
        assert overview.execution.planned
        assert overview.weekly_plan.this_week
        assert overview.weekly_plan.priority_focus
        assert overview.project_health[0].project_title == "Founder Dashboard"
        assert overview.suggestions
        assert progress.current_progress == 0
        assert progress.remaining_work
