import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.dependencies import get_current_user, get_db
from app.database.base import Base
from app.database.session import _ensure_local_project_intelligence_phase2_schema
from app.main import app
from app.models.user import User


@pytest.fixture
def client(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'project-intelligence.db'}")

    async def create_schema():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    user = User(id=uuid4(), email="project-intelligence@example.com", is_active=True)

    async def override_user():
        return user

    async def override_db():
        async with session_factory() as session:
            session.add(user)
            await session.flush()
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_project_intelligence_api_lifecycle(client):
    created = client.post(
        "/api/projects",
        json={
            "name": "Synzept V2",
            "description": "Continuity operating system",
            "currentFocus": "Project Intelligence",
            "recommendedNextStep": "Wire open loops and decisions",
        },
    )
    assert created.status_code == 200
    project = created.json()
    assert project["name"] == "Synzept V2"
    assert project["currentFocus"] == "Project Intelligence"
    assert project["recommendedNextStep"] == "Wire open loops and decisions"

    project_id = project["id"]
    fetched = client.get(f"/api/projects/{project_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == project_id

    updated = client.put(
        f"/api/projects/{project_id}",
        json={
            "currentFocus": "Phase 2 validation",
            "recommendedNextStep": "Commit Project Intelligence",
            "status": "active",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["currentFocus"] == "Phase 2 validation"
    assert updated.json()["recommendedNextStep"] == "Commit Project Intelligence"

    loop = client.post(
        f"/api/projects/{project_id}/open-loops",
        json={"title": "Finish API tests", "description": "Needed before Phase 2 commit"},
    )
    assert loop.status_code == 200
    loop_id = loop.json()["id"]
    assert client.get(f"/api/projects/{project_id}/open-loops").json()[0]["title"] == "Finish API tests"

    completed_loop = client.put(f"/api/open-loops/{loop_id}", json={"status": "completed"})
    assert completed_loop.status_code == 200
    assert completed_loop.json()["status"] == "completed"

    decision = client.post(
        f"/api/projects/{project_id}/decisions",
        json={"title": "Use exact /api routes", "description": "Matches Phase 2 contract"},
    )
    assert decision.status_code == 200
    decision_id = decision.json()["id"]
    assert client.get(f"/api/projects/{project_id}/decisions").json()[0]["status"] == "pending"

    decided = client.put(f"/api/decisions/{decision_id}", json={"status": "decided"})
    assert decided.status_code == 200
    assert decided.json()["status"] == "decided"

    assert client.delete(f"/api/decisions/{decision_id}").status_code == 200
    assert client.delete(f"/api/open-loops/{loop_id}").status_code == 200
    assert client.delete(f"/api/projects/{project_id}").status_code == 200
    assert client.get(f"/api/projects/{project_id}").status_code == 404


@pytest.mark.asyncio
async def test_existing_sqlite_project_tables_get_phase2_columns(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'legacy-projects.db'}")
    async with engine.begin() as connection:
        await connection.exec_driver_sql("CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
        await connection.run_sync(_ensure_local_project_intelligence_phase2_schema)
        columns = {row[1] for row in await connection.exec_driver_sql("PRAGMA table_info(projects)")}
        assert {"current_focus", "recommended_next_step"} <= columns
    await engine.dispose()
