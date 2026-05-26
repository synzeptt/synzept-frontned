from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.schemas.task import TaskUpdate
from app.tasks.service import TaskService


class _TaskUpdateSession:
    def __init__(self, task):
        self.task = task
        self.flushed = False
        self.refreshed = False

    async def get(self, _model, _task_id):
        return self.task

    async def flush(self):
        self.flushed = True

    async def refresh(self, item):
        self.refreshed = item is self.task


def test_app_metadata_is_configured():
    assert app.title == "Synzept API"
    assert app.version == "1.0.0"


def test_settings_have_local_development_defaults():
    settings = get_settings()

    assert settings.environment == "development"
    assert settings.database_url.startswith(("sqlite+aiosqlite://", "postgresql+asyncpg://"))
    assert "http://localhost:3000" in settings.cors_origin_list
    assert "http://127.0.0.1:3000" in settings.cors_origin_list


def test_health_endpoint_returns_foundation_payload():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "synzept-backend"
    assert payload["environment"]
    assert payload["database"] in {"connected", "unavailable"}
    assert payload["status"] in {"ok", "degraded"}


def test_local_frontend_origins_receive_cors_headers():
    client = TestClient(app)

    for origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
        response = client.options(
            "/api/v1/tasks",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "PATCH",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
        assert response.headers["access-control-allow-credentials"] == "true"
        assert "PATCH" in response.headers["access-control-allow-methods"]
        assert "authorization" in response.headers["access-control-allow-headers"].lower()
        assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_task_patch_auth_failures_still_include_cors_headers():
    client = TestClient(app)

    response = client.patch(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000000",
        headers={"Origin": "http://localhost:3000", "Authorization": "Bearer invalid"},
        json={"status": "completed"},
    )

    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.asyncio
async def test_task_update_refreshes_server_updated_columns_before_response():
    user_id = uuid4()
    task_id = uuid4()
    task = SimpleNamespace(id=task_id, user_id=user_id, deleted_at=None, status="todo")
    session = _TaskUpdateSession(task)

    updated = await TaskService(session).update(task_id, user_id, TaskUpdate(status="completed"))

    assert updated is task
    assert task.status == "completed"
    assert session.flushed is True
    assert session.refreshed is True
