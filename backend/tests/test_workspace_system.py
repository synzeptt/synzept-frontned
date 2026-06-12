from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database.base import Base
from app.database.session import _ensure_local_workspace_schema
from app.models.task import Task
from app.models.user import User
from app.schemas.goal import GoalCreate, MilestoneCreate
from app.schemas.note import NoteCreate
from app.schemas.project import ProjectCreate
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.goal_progress_service import GoalProgressService
from app.services.workspace_service import WorkspaceService
from app.tasks.service import TaskService


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'workspace.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_workspace_unifies_project_goal_task_note_search_progress_and_timeline(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        session.add(User(id=user_id, email="workspace@example.com"))
        await session.flush()
        workspace = WorkspaceService(session)
        project = await workspace.create_project(user_id, ProjectCreate(name="Synzept", description="Continuity workspace"))
        goal = await GoalProgressService(session).create_goal(
            user_id,
            GoalCreate(title="Launch Synzept", project_id=project.id),
        )
        goal = await GoalProgressService(session).create_milestone(
            user_id,
            goal.id,
            MilestoneCreate(title="Build Workspace System"),
        )
        goal = await GoalProgressService(session).create_task(
            user_id,
            goal.id,
            goal.milestones[0].id,
            TaskCreate(title="Create unified search", priority="high"),
        )
        task = goal.milestones[0].tasks[0]
        await workspace.create_note(
            user_id,
            NoteCreate(
                title="Synzept workspace notes",
                content="Rich text **workspace** decision.",
                project_id=project.id,
                goal_id=goal.id,
                tags=["Synzept", " workspace ", "synzept"],
            ),
        )
        await TaskService(session).update(task.id, user_id, TaskUpdate(status="completed"))

        payload = await workspace.get_workspace(user_id)
        assert payload.projects[0].title == "Synzept"
        assert payload.projects[0].goals[0].title == "Launch Synzept"
        assert payload.projects[0].notes[0].tags == ["synzept", "workspace"]
        assert payload.progress.goal_completion == 100.0
        assert payload.progress.project_completion == 100.0
        assert payload.progress.task_completion == 100.0

        search = await workspace.search(user_id, "Synzept")
        assert {"project", "goal", "note"} <= {item.type for item in search.results}

        timeline = await workspace.timeline(user_id)
        assert "project_created" in {item.action for item in timeline}
        assert "task_completed" in {item.action for item in timeline}
        assert "goal_completed" in {item.action for item in timeline}


@pytest.mark.asyncio
async def test_workspace_insights_surface_stalled_projects_and_overdue_tasks(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        session.add(User(id=user_id, email="insights@example.com"))
        await session.flush()
        workspace = WorkspaceService(session)
        project = await workspace.create_project(user_id, ProjectCreate(name="Stalled project"))
        raw_project = await workspace._owned_project(user_id, project.id)
        raw_project.updated_at = datetime.now(timezone.utc) - timedelta(days=8)
        session.add(
            Task(
                user_id=user_id,
                project_id=project.id,
                title="Overdue workspace task",
                status="todo",
                priority="high",
                due_at=datetime.now(timezone.utc) - timedelta(days=1),
            )
        )
        await session.flush()

        insights = await workspace.insights(user_id)

        assert {"stalled_project", "overdue_task"} <= {item.type for item in insights}


@pytest.mark.asyncio
async def test_existing_sqlite_notes_table_gets_workspace_columns(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'legacy-workspace.db'}")
    async with engine.begin() as connection:
        await connection.exec_driver_sql("CREATE TABLE notes (id TEXT PRIMARY KEY)")
        await connection.run_sync(_ensure_local_workspace_schema)
        columns = {row[1] for row in await connection.exec_driver_sql("PRAGMA table_info(notes)")}
        assert {"goal_id", "tags"} <= columns
    await engine.dispose()
