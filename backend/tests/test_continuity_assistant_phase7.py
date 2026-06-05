import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.dependencies import get_current_user, get_db
from app.database.base import Base
from app.main import app
from app.models.user import User


@pytest.fixture
def client(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'continuity-assistant.db'}")

    async def create_schema():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    user = User(id=uuid4(), email="continuity-assistant@example.com", is_active=True)

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


def test_continuity_assistant_uses_context_engine_outputs(client):
    project = client.post(
        "/api/projects",
        json={
            "name": "Continuity Assistant",
            "currentFocus": "Help returning users resume",
            "recommendedNextStep": "Show what changed first",
        },
    ).json()
    client.post(
        f"/api/projects/{project['id']}/open-loops",
        json={"title": "Explain unfinished work", "description": "Open loops should be visible on return."},
    )
    progress = client.post(
        "/api/timeline-events",
        json={
            "eventType": "progress",
            "title": "Context Engine shipped",
            "description": "The assistant can now reuse context.",
            "eventDate": "2026-06-05",
            "projectId": project["id"],
        },
    )
    assert progress.status_code == 200

    response = client.post("/api/continuity-assistant/refresh")
    assert response.status_code == 200
    body = response.json()
    assert body["recommendedNextStep"]["title"] == "Show what changed first"
    assert body["openLoops"][0]["title"] == "Explain unfinished work"
    assert body["whatChanged"][0]["title"] == "Context Engine shipped"
    assert body["recentProgress"][0]["title"] == "Context Engine shipped"
    assert body["contextSnapshotId"]

    fetched = client.get("/api/continuity-assistant")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]
