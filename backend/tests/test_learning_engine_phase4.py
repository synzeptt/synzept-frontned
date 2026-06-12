import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.dependencies import get_current_user, get_db, require_pro_user
from app.database.base import Base
from app.database.session import _ensure_local_learning_engine_phase4_schema
from app.main import app
from app.models.user import User


@pytest.fixture
def client(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'learning-engine.db'}")

    async def create_schema():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    user = User(id=uuid4(), email="learning-engine@example.com", is_active=True)

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


def test_learning_engine_observes_analyzes_and_waits_for_approval(client):
    first = client.post(
        "/api/learning-engine/observations",
        json={"source": "project", "content": "User is shaping startup launch priorities."},
    )
    assert first.status_code == 200
    assert first.json()["status"] == "observed"

    second = client.post(
        "/api/learning-engine/observations",
        json={"source": "note", "content": "Another startup project needs a concise next step."},
    )
    assert second.status_code == 200

    overview = client.get("/api/learning-engine")
    assert overview.status_code == 200
    assert len(overview.json()["observations"]) == 2

    analysis = client.post("/api/learning-engine/analyze")
    assert analysis.status_code == 200
    analyzed = analysis.json()
    assert analyzed["observationsAnalyzed"] == 2
    assert analyzed["suggestionsCreated"] >= 1

    understanding_before_accept = client.get("/api/user-understanding")
    assert understanding_before_accept.status_code == 200
    assert understanding_before_accept.json()["learning"] == {}

    suggestion = next(item for item in analyzed["suggestions"] if item["status"] == "pending")
    accepted = client.put(f"/api/learning-suggestions/{suggestion['id']}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    understanding_after_accept = client.get("/api/user-understanding")
    assert understanding_after_accept.status_code == 200
    assert accepted.json()["description"] in understanding_after_accept.json()["learning"]["topicsInterestedIn"]


def test_learning_engine_suggestion_edit_and_ignore(client):
    created = client.post(
        "/api/learning-suggestions",
        json={"title": "Draft learning", "description": "A suggestion waiting for user control."},
    )
    assert created.status_code == 200

    edited = client.put(
        f"/api/learning-suggestions/{created.json()['id']}/edit",
        json={"title": "Edited learning", "description": "User refined the suggestion before deciding."},
    )
    assert edited.status_code == 200
    assert edited.json()["title"] == "Edited learning"

    ignored = client.put(f"/api/learning-suggestions/{created.json()['id']}/ignore")
    assert ignored.status_code == 200
    assert ignored.json()["status"] == "ignored"


@pytest.mark.asyncio
async def test_existing_sqlite_learning_observation_tables_get_phase4_columns(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'legacy-learning.db'}")
    async with engine.begin() as connection:
        await connection.exec_driver_sql("CREATE TABLE learning_observations (id TEXT PRIMARY KEY)")
        await connection.run_sync(_ensure_local_learning_engine_phase4_schema)
        columns = {row[1] for row in await connection.exec_driver_sql("PRAGMA table_info(learning_observations)")}
        assert {"source", "content", "status", "updated_at"}.issubset(columns)
    await engine.dispose()
