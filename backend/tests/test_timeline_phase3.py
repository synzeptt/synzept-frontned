import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.dependencies import get_current_user, get_db
from app.database.base import Base
from app.database.session import _ensure_local_timeline_phase3_schema
from app.main import app
from app.models.user import User


@pytest.fixture
def client(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'timeline.db'}")

    async def create_schema():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    user = User(id=uuid4(), email="timeline@example.com", is_active=True)

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


def test_timeline_event_api_lifecycle(client):
    project = client.post(
        "/api/projects",
        json={"name": "Timeline Project", "currentFocus": "Meaningful history", "recommendedNextStep": "Add events"},
    ).json()

    created = client.post(
        "/api/timeline-events",
        json={
            "eventType": "milestone",
            "title": "Project Intelligence shipped",
            "description": "Phase 2 became the foundation for continuity.",
            "eventDate": "2026-06-05",
            "importance": 0.9,
            "projectId": project["id"],
        },
    )
    assert created.status_code == 200
    event = created.json()
    assert event["eventType"] == "milestone"
    assert event["projectId"] == project["id"]

    listed = client.get("/api/timeline-events")
    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "Project Intelligence shipped"

    filtered = client.get(f"/api/timeline-events?project_id={project['id']}")
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1

    updated = client.put(
        f"/api/timeline-events/{event['id']}",
        json={"eventType": "progress", "title": "Timeline captured progress", "importance": 0.7},
    )
    assert updated.status_code == 200
    assert updated.json()["eventType"] == "progress"
    assert updated.json()["importance"] == 0.7

    assert client.delete(f"/api/timeline-events/{event['id']}").status_code == 200
    assert client.get(f"/api/timeline-events/{event['id']}").status_code == 404


@pytest.mark.asyncio
async def test_existing_sqlite_timeline_tables_get_phase3_columns(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'legacy-timeline.db'}")
    async with engine.begin() as connection:
        await connection.exec_driver_sql("CREATE TABLE timeline_events (id TEXT PRIMARY KEY)")
        await connection.run_sync(_ensure_local_timeline_phase3_schema)
        columns = {row[1] for row in await connection.exec_driver_sql("PRAGMA table_info(timeline_events)")}
        assert "project_id" in columns
    await engine.dispose()
