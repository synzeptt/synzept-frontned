from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database.base import Base
from app.database.session import _ensure_local_goal_schema
from app.models.user import User
from app.schemas.goal import GoalCreate, MilestoneCreate
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.goal_progress_service import GoalProgressService
from app.tasks.service import TaskService


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'goals.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_task_completion_rolls_up_milestone_and_goal_progress(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        session.add(User(id=user_id, email="goals@example.com"))
        await session.flush()
        service = GoalProgressService(session)
        goal = await service.create_goal(user_id, GoalCreate(title="Launch Synzept"))
        goal = await service.create_milestone(user_id, goal.id, MilestoneCreate(title="Build Memory System"))
        milestone = goal.milestones[0]
        goal = await service.create_task(user_id, goal.id, milestone.id, TaskCreate(title="Design Schema"))
        goal = await service.create_task(user_id, goal.id, milestone.id, TaskCreate(title="Create Storage Layer"))

        first_task = goal.milestones[0].tasks[0]
        await TaskService(session).update(first_task.id, user_id, TaskUpdate(status="completed"))
        goal = await service.get_goal(user_id, goal.id)
        assert goal.milestones[0].progress == 50.0
        assert goal.progress == 0.0

        second_task = next(task for task in goal.milestones[0].tasks if task.id != first_task.id)
        await TaskService(session).update(second_task.id, user_id, TaskUpdate(status="completed"))
        goal = await service.get_goal(user_id, goal.id)
        assert goal.milestones[0].status == "completed"
        assert goal.milestones[0].progress == 100.0
        assert goal.status == "completed"
        assert goal.progress == 100.0


@pytest.mark.asyncio
async def test_next_actions_weekly_review_and_dashboard(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        session.add(User(id=user_id, email="dashboard@example.com"))
        await session.flush()
        service = GoalProgressService(session)
        goal = await service.create_goal(user_id, GoalCreate(title="Launch Synzept"))
        goal = await service.create_milestone(user_id, goal.id, MilestoneCreate(title="Build Progress Engine"))
        milestone = goal.milestones[0]
        await service.create_task(
            user_id,
            goal.id,
            milestone.id,
            TaskCreate(title="Write retrieval tests", priority="medium"),
        )
        goal = await service.create_task(
            user_id,
            goal.id,
            milestone.id,
            TaskCreate(title="Finish dashboard API", priority="high"),
        )

        actions = await service.next_actions(user_id)
        assert actions[0].title == "Finish dashboard API"
        assert actions[0].goal_title == "Launch Synzept"

        completed_task = next(task for task in goal.milestones[0].tasks if task.title == "Write retrieval tests")
        await TaskService(session).update(completed_task.id, user_id, TaskUpdate(status="completed"))
        review = await service.weekly_review(user_id)
        assert "Write retrieval tests" in review.completed
        assert "Finish dashboard API" in review.blocked

        dashboard = await service.dashboard(user_id)
        assert dashboard.active_goals[0].title == "Launch Synzept"
        assert dashboard.recommendations[0].title == "Finish dashboard API"
        assert dashboard.upcoming_tasks[0].title == "Finish dashboard API"


@pytest.mark.asyncio
async def test_existing_sqlite_task_table_gets_milestone_column(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'legacy-goals.db'}")
    async with engine.begin() as connection:
        await connection.exec_driver_sql("CREATE TABLE tasks (id TEXT PRIMARY KEY)")
        await connection.run_sync(_ensure_local_goal_schema)
        columns = await connection.exec_driver_sql("PRAGMA table_info(tasks)")
        assert "milestone_id" in {row[1] for row in columns}
    await engine.dispose()
