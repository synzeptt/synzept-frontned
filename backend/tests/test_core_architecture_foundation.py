from datetime import date
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.exceptions import NotFoundError
from app.database.base import Base
from app.database.session import _ensure_local_core_schema
from app.models.user import User
from app.schemas.core import (
    CoreGoalCreate,
    CoreGoalUpdate,
    CoreMemoryCreate,
    CoreMemoryUpdate,
    CoreProjectCreate,
    CoreProjectUpdate,
    GraphEdgeCreate,
    GraphEdgeUpdate,
    GraphNodeCreate,
    LearningSignalCreate,
    LearningSignalUpdate,
    TimelineEventCreate,
    TimelineEventUpdate,
)
from app.services.goal_service import GoalService
from app.services.graph_service import GraphService
from app.services.learning_service import LearningService
from app.services.memory_service import CoreMemoryService
from app.services.project_service import ProjectService
from app.services.timeline_service import TimelineService


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'core.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_core_services_share_owned_crud_foundation(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        session.add(User(id=user_id, email="core@example.com"))
        await session.flush()

        project_service = ProjectService(session)
        project = await project_service.create(user_id, CoreProjectCreate(title="Core Architecture"))
        project = await project_service.update(user_id, project.id, CoreProjectUpdate(title="Shared Architecture"))
        assert project.name == project.title == "Shared Architecture"

        goal_service = GoalService(session)
        goal = await goal_service.create(user_id, CoreGoalCreate(title="Ship foundation"))
        goal = await goal_service.update(user_id, goal.id, CoreGoalUpdate(target_date=date(2026, 7, 1)))
        assert goal.target_date == date(2026, 7, 1)

        memory_service = CoreMemoryService(session)
        memory = await memory_service.create(
            user_id,
            CoreMemoryCreate(memory_type="decision", content="Use one V2 core schema.", confidence=0.9, source="manual"),
        )
        memory = await memory_service.update(user_id, memory.id, CoreMemoryUpdate(confidence=0.95))
        assert memory.confidence == 0.95
        assert memory.source == "manual"

        timeline_service = TimelineService(session)
        event = await timeline_service.create(
            user_id,
            TimelineEventCreate(event_type="decision", title="Core model chosen", event_date=date(2026, 6, 2)),
        )
        event = await timeline_service.update(user_id, event.id, TimelineEventUpdate(importance=0.8))
        assert event.importance == 0.8

        learning_service = LearningService(session)
        signal = await learning_service.create(
            user_id,
            LearningSignalCreate(signal_type="preference", content="Prefers stable shared architecture."),
        )
        signal = await learning_service.update(user_id, signal.id, LearningSignalUpdate(status="accepted"))
        assert signal.status == "accepted"

        graph_service = GraphService(session)
        source = await graph_service.create_node(user_id, GraphNodeCreate(node_type="person", title="User"))
        target = await graph_service.create_node(user_id, GraphNodeCreate(node_type="project", title="Shared Architecture"))
        edge = await graph_service.create_edge(
            user_id,
            GraphEdgeCreate(source_node_id=source.id, target_node_id=target.id, relationship_type="owns"),
        )
        edge = await graph_service.update_edge(user_id, edge.id, GraphEdgeUpdate(strength=0.9))
        assert edge.strength == 0.9

        assert len(await project_service.list(user_id)) == 1
        assert len(await goal_service.list(user_id)) == 1
        assert len(await memory_service.list(user_id)) == 1
        assert len(await timeline_service.list(user_id)) == 1
        assert len(await learning_service.list(user_id)) == 1
        assert len(await graph_service.list_nodes(user_id)) == 2
        assert len(await graph_service.list_edges(user_id)) == 1

        await graph_service.delete_edge(user_id, edge.id)
        await timeline_service.delete(user_id, event.id)
        await learning_service.delete(user_id, signal.id)
        await memory_service.delete(user_id, memory.id)
        await goal_service.delete(user_id, goal.id)
        await project_service.delete(user_id, project.id)
        await session.flush()

        assert await memory_service.list(user_id) == []
        assert await goal_service.list(user_id) == []
        assert await project_service.list(user_id) == []


@pytest.mark.asyncio
async def test_core_services_reject_cross_user_access_and_graph_links(session_factory):
    owner_id = uuid4()
    other_id = uuid4()
    async with session_factory() as session:
        session.add_all([User(id=owner_id, email="owner@example.com"), User(id=other_id, email="other@example.com")])
        await session.flush()

        project = await ProjectService(session).create(owner_id, CoreProjectCreate(title="Private"))
        with pytest.raises(NotFoundError):
            await ProjectService(session).get(other_id, project.id)

        owner_node = await GraphService(session).create_node(owner_id, GraphNodeCreate(node_type="person", title="Owner"))
        other_node = await GraphService(session).create_node(other_id, GraphNodeCreate(node_type="person", title="Other"))
        with pytest.raises(NotFoundError):
            await GraphService(session).create_edge(
                owner_id,
                GraphEdgeCreate(source_node_id=owner_node.id, target_node_id=other_node.id, relationship_type="knows"),
            )


@pytest.mark.asyncio
async def test_existing_sqlite_tables_get_canonical_core_columns(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'legacy-core.db'}")
    async with engine.begin() as connection:
        await connection.exec_driver_sql("CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
        await connection.exec_driver_sql("INSERT INTO projects (id, name) VALUES ('project-1', 'Legacy Project')")
        await connection.exec_driver_sql("CREATE TABLE goals (id TEXT PRIMARY KEY)")
        await connection.exec_driver_sql("CREATE TABLE memories (id TEXT PRIMARY KEY)")
        await connection.run_sync(_ensure_local_core_schema)
        project_columns = {row[1] for row in await connection.exec_driver_sql("PRAGMA table_info(projects)")}
        goal_columns = {row[1] for row in await connection.exec_driver_sql("PRAGMA table_info(goals)")}
        memory_columns = {row[1] for row in await connection.exec_driver_sql("PRAGMA table_info(memories)")}
        title = (await connection.exec_driver_sql("SELECT title FROM projects WHERE id = 'project-1'")).scalar_one()
        assert "title" in project_columns
        assert "target_date" in goal_columns
        assert {"confidence", "source"} <= memory_columns
        assert title == "Legacy Project"
    await engine.dispose()
