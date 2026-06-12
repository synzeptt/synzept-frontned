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
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'context-engine.db'}")

    async def create_schema():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    user = User(id=uuid4(), email="context-engine@example.com", is_active=True)

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


def test_context_engine_outputs_single_source_context(client):
    project = client.post(
        "/api/projects",
        json={
            "name": "Context Engine",
            "description": "Single source of continuity truth",
            "currentFocus": "Unify continuity signals",
            "recommendedNextStep": "Use Context Engine for return flows",
        },
    ).json()
    loop = client.post(
        f"/api/projects/{project['id']}/open-loops",
        json={"title": "Wire future assistants to context", "description": "Avoid duplicate context calculations."},
    )
    assert loop.status_code == 200
    event = client.post(
        "/api/timeline-events",
        json={
            "eventType": "decision",
            "title": "Context owns continuity output",
            "eventDate": "2026-06-05",
            "projectId": project["id"],
        },
    )
    assert event.status_code == 200
    suggestion = client.post(
        "/api/learning-suggestions",
        json={"title": "Continuity systems", "description": "User repeatedly focuses on continuity."},
    )
    assert suggestion.status_code == 200

    project_node = client.post(
        "/api/relationship-graph/nodes",
        json={"nodeType": "project", "entityId": project["id"], "title": "Context Engine"},
    ).json()
    decision_node = client.post(
        "/api/relationship-graph/nodes",
        json={"nodeType": "decision", "entityId": event.json()["id"], "title": "Context owns output"},
    ).json()
    edge = client.post(
        "/api/relationship-graph/edges",
        json={
            "sourceNodeId": decision_node["id"],
            "targetNodeId": project_node["id"],
            "relationshipType": "explains",
            "reason": "Future assistants must use the Context Engine.",
        },
    )
    assert edge.status_code == 200

    context = client.post("/api/context-engine/refresh")
    assert context.status_code == 200
    body = context.json()
    assert body["currentFocus"]["title"] == "Context Engine"
    assert body["currentFocus"]["detail"] == "Unify continuity signals"
    assert body["recommendedNextStep"]["title"] == "Use Context Engine for return flows"
    assert body["openLoops"][0]["title"] == "Wire future assistants to context"
    assert any(item["title"] == "Continuity systems" for item in body["activeThemes"])
    assert any(item["type"] == "relationship" for item in body["importantContext"])

    fetched = client.get("/api/context-engine")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


def test_context_engine_empty_state_is_explainable(client):
    context = client.get("/api/context-engine")
    assert context.status_code == 200
    body = context.json()
    assert body["currentFocus"]["title"] == "No current focus set."
    assert body["recommendedNextStep"]["title"] == "Define the next action to keep momentum."
