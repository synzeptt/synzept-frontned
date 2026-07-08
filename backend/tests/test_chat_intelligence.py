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
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'chat-intelligence.db'}")

    async def create_schema():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    user = User(id=uuid4(), email="chat-intelligence@example.com", is_active=True)

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


def test_chat_context_and_history_summary_endpoints(client):
    context_response = client.post("/api/chat/context", json={})
    assert context_response.status_code == 200
    context_body = context_response.json()
    assert context_body["who_the_user_is"]["user_id"]
    assert "active_projects" in context_body
    assert "open_loops" in context_body
    assert "recent_progress" in context_body
    assert "recent_decisions" in context_body
    assert "suggested_next_actions" in context_body

    history_response = client.get("/api/chat/history-summary?limit=5")
    assert history_response.status_code == 200
    history_body = history_response.json()
    assert isinstance(history_body, list)
    assert history_body == []


def test_chat_continue_endpoint_returns_context(client):
    response = client.post("/api/chat/continue", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["headline"].startswith("Welcome back")
    assert "cards" in body
    assert isinstance(body["cards"], list)
    assert "context_used" in body
