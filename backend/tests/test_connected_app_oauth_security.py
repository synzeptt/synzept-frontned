from types import SimpleNamespace

import pytest

from app.core.exceptions import AppError
from app.services.connected_apps.google_calendar_service import GoogleCalendarService
from app.services.connected_apps.oauth_lifecycle import ConnectedAppOAuthLifecycle


@pytest.mark.asyncio
async def test_google_calendar_callback_rejects_invalid_state_before_missing_code_redirect(monkeypatch):
    service = GoogleCalendarService(SimpleNamespace())
    monkeypatch.setattr(service, "_require_config", lambda: None)

    with pytest.raises(AppError, match="Invalid Google OAuth state"):
        await service.handle_callback(code=None, state="invalid", error=None)


@pytest.mark.asyncio
async def test_oauth_nonce_is_consumed_once(monkeypatch):
    account = SimpleNamespace(id="account-1", app_metadata={"oauth_state_nonce": "nonce"})
    locked = SimpleNamespace(id="account-1", app_metadata={"oauth_state_nonce": "nonce"})

    class Result:
        def scalar_one(self):
            return locked

    class Session:
        async def execute(self, _query):
            return Result()

        async def flush(self):
            return None

    lifecycle = ConnectedAppOAuthLifecycle(Session())
    await lifecycle.consume_state_nonce(account, "nonce", "provider")
    assert locked.app_metadata == {}

    locked.app_metadata = {"oauth_state_nonce": "other"}
    with pytest.raises(AppError, match="Invalid provider OAuth state"):
        await lifecycle.consume_state_nonce(account, "nonce", "provider")
