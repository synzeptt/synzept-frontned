import shutil
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import attachments as attachments_module
from app.core.dependencies import get_current_user
from app.main import app
from app.models.user import User


@pytest.fixture
def client(tmp_path, monkeypatch):
    user = User(id=uuid4(), email="attachment-test@example.com", is_active=True)

    async def override_user():
        return user

    monkeypatch.setattr(attachments_module, "BASE_ATTACHMENT_DIR", tmp_path / "attachments")
    (tmp_path / "attachments").mkdir(parents=True, exist_ok=True)

    app.dependency_overrides[get_current_user] = override_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_upload_and_retrieve_attachment(client):
    response = client.post(
        "/api/v1/attachments",
        files={"file": ("test.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["filename"] == "test.txt"
    assert body["size"] == len(b"hello world")
    assert body["content_type"] == "text/plain"
    assert "id" in body
    assert "url" in body

    get_response = client.get(body["url"])
    assert get_response.status_code == 200
    assert get_response.content == b"hello world"
    assert get_response.headers["content-type"].startswith("text/plain")
