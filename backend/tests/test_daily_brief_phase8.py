import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.dependencies import get_current_user, get_db, require_pro_user
from app.database.base import Base
from app.main import app
from app.models.user import User


@pytest.fixture
def client(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'daily-brief.db'}")

    async def create_schema():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    user = User(id=uuid4(), email="daily-brief@example.com", is_active=True)

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
    app.dependency_overrides[require_pro_user] = override_user
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_daily_brief_is_powered_by_context_engine(client):
    project = client.post(
        "/api/projects",
        json={
            "name": "Daily Brief",
            "currentFocus": "Show what matters today",
            "recommendedNextStep": "Review the open loop",
        },
    ).json()
    client.post(
        f"/api/projects/{project['id']}/open-loops",
        json={"title": "Finish Phase 8 validation", "description": "Daily Brief should reuse context."},
    )
    client.post(
        "/api/timeline-events",
        json={
            "eventType": "achievement",
            "title": "Continuity Assistant shipped",
            "description": "Return flow now works.",
            "eventDate": "2026-06-05",
            "projectId": project["id"],
        },
    )

    response = client.post("/api/daily-brief/refresh")
    assert response.status_code == 200
    body = response.json()
    assert body["recommendedNextStep"]["title"] == "Review the open loop"
    assert body["whatMattersToday"][0]["title"] == "Daily Brief"
    assert body["openLoops"][0]["title"] == "Finish Phase 8 validation"
    assert body["recentProgress"][0]["title"] == "Continuity Assistant shipped"
    assert body["whatChanged"][0]["title"] == "Continuity Assistant shipped"
    assert body["whatMattersToday"]
    assert body["openLoops"]
    assert body["recommendedNextStep"]["title"]
    assert body["focusForToday"]["title"]
    assert body["contextSnapshotId"]

    fetched = client.get("/api/daily-brief")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]

    history = client.get("/api/daily-brief/history?limit=7")
    assert history.status_code == 200
    assert history.json()[0]["id"] == body["id"]


def test_daily_brief_history_requires_valid_limit(client):
    response = client.get("/api/daily-brief/history?limit=100")

    assert response.status_code == 422
