from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_refresh_token, hash_password, verify_password
from app.core.exceptions import AppError
from app.main import app
from app.models.refresh_token import RefreshToken
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.auth import SignupRequest
from app.services.auth_service import AuthService
from app.services.google_auth_service import GoogleAuthService


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _Session:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.added = []
        self.statements = []
        self.deleted = []

    async def execute(self, _statement):
        self.statements.append(_statement)
        if self.results:
            return _Result(self.results.pop(0))
        return _Result(None)

    def add(self, item):
        self.added.append(item)

    async def get(self, model, item_id):
        for item in self.added:
            if isinstance(item, model) and getattr(item, "id", None) == item_id:
                return item
        for item in self.results:
            if isinstance(item, model) and getattr(item, "id", None) == item_id:
                return item
        return None

    async def delete(self, item):
        self.deleted.append(item)
        if item in self.added:
            self.added.remove(item)

    async def flush(self):
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid4()


def test_password_hashing_does_not_store_plaintext():
    hashed = hash_password("correct-password")

    assert hashed != "correct-password"
    assert verify_password("correct-password", hashed)
    assert not verify_password("wrong-password", hashed)


@pytest.mark.asyncio
async def test_signup_creates_user_profile_and_tokens():
    session = _Session(results=[None])

    tokens, user = await AuthService(session).signup(
        SignupRequest(email="User@Example.com", password="correct-password", display_name="User")
    )

    assert user.email == "user@example.com"
    assert user.password_hash != "correct-password"
    assert user.is_active is True
    assert user.is_verified is False
    assert tokens.access_token
    assert tokens.refresh_token
    assert any(isinstance(item, UserProfile) for item in session.added)
    assert any(isinstance(item, RefreshToken) for item in session.added)


@pytest.mark.asyncio
async def test_login_verifies_credentials_and_issues_tokens():
    user = User(
        id=uuid4(),
        email="user@example.com",
        password_hash=hash_password("correct-password"),
        is_active=True,
    )
    session = _Session(results=[user])

    tokens, logged_in = await AuthService(session).login("USER@example.com", "correct-password")

    assert logged_in.id == user.id
    assert tokens.access_token
    assert tokens.refresh_token
    assert any(isinstance(item, RefreshToken) for item in session.added)


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials_with_safe_message():
    user = User(
        id=uuid4(),
        email="user@example.com",
        password_hash=hash_password("correct-password"),
        is_active=True,
    )
    session = _Session(results=[user])

    with pytest.raises(AppError) as exc_info:
        await AuthService(session).login("user@example.com", "wrong-password")

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "invalid_credentials"
    assert exc_info.value.user_message == "Invalid email or password."


@pytest.mark.asyncio
async def test_refresh_revokes_existing_token_and_issues_new_pair():
    user_id = uuid4()
    refresh = create_refresh_token(user_id, "test-jti")
    stored = RefreshToken(
        user_id=user_id,
        token_hash=__import__("hashlib").sha256(refresh.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    session = _Session(results=[stored])

    tokens = await AuthService(session).refresh(refresh)

    assert stored.revoked_at is not None
    assert tokens.access_token
    assert tokens.refresh_token
    assert tokens.refresh_token != refresh


@pytest.mark.asyncio
async def test_refresh_accepts_naive_utc_expiry_from_database():
    user_id = uuid4()
    refresh = create_refresh_token(user_id, "test-jti")
    stored = RefreshToken(
        user_id=user_id,
        token_hash=__import__("hashlib").sha256(refresh.encode()).hexdigest(),
        expires_at=(datetime.now(timezone.utc) + timedelta(days=1)).replace(tzinfo=None),
    )
    session = _Session(results=[stored])

    tokens = await AuthService(session).refresh(refresh)

    assert stored.revoked_at is not None
    assert stored.revoked_at.tzinfo is not None
    assert tokens.access_token
    assert tokens.refresh_token


@pytest.mark.asyncio
async def test_forgot_password_creates_reset_token_and_sends_calm_email(monkeypatch):
    sent = {}
    user = User(id=uuid4(), email="user@example.com", password_hash=hash_password("old-password"), is_active=True)
    session = _Session(results=[user])

    monkeypatch.setattr(
        "app.services.auth_service.EmailService.send_password_reset",
        lambda self, **kwargs: sent.update(kwargs),
    )

    await AuthService(session).forgot_password("USER@example.com")

    reset_tokens = [item for item in session.added if isinstance(item, PasswordResetToken)]
    assert len(reset_tokens) == 1
    assert reset_tokens[0].token_hash
    assert sent["email"] == "user@example.com"
    assert "/reset-password?token=" in sent["reset_url"]


@pytest.mark.asyncio
async def test_forgot_password_does_not_reveal_unknown_email(monkeypatch):
    sent = {}
    session = _Session(results=[None])
    monkeypatch.setattr(
        "app.services.auth_service.EmailService.send_password_reset",
        lambda self, **kwargs: sent.update(kwargs),
    )

    await AuthService(session).forgot_password("missing@example.com")

    assert sent == {}
    assert not any(isinstance(item, PasswordResetToken) for item in session.added)


@pytest.mark.asyncio
async def test_reset_password_updates_hash_uses_token_and_revokes_sessions():
    plain = "reset-token"
    user = User(id=uuid4(), email="user@example.com", password_hash=hash_password("old-password"), is_active=True)
    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=__import__("hashlib").sha256(plain.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    session = _Session(results=[reset_token, user])

    await AuthService(session).reset_password(plain, "new-password")

    assert reset_token.used_at is not None
    assert verify_password("new-password", user.password_hash)


@pytest.mark.asyncio
async def test_delete_account_requires_confirmation_and_password():
    user = User(id=uuid4(), email="user@example.com", password_hash=hash_password("current-password"), is_active=True)
    session = _Session()

    with pytest.raises(AppError) as exc_info:
        await AuthService(session).delete_account(user, "wrong-password", "DELETE")

    assert exc_info.value.status_code == 401
    assert user not in session.deleted


@pytest.mark.asyncio
async def test_delete_account_executes_backend_cleanup():
    user = User(id=uuid4(), email="user@example.com", password_hash=hash_password("current-password"), is_active=True)
    session = _Session()

    await AuthService(session).delete_account(user, "current-password", "DELETE")

    assert user in session.deleted
    assert len(session.statements) >= 14


def test_protected_route_rejects_missing_token():
    client = TestClient(app)

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_protected_route_rejects_invalid_token():
    client = TestClient(app)

    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_google_signup_creates_verified_user_and_profile(monkeypatch):
    monkeypatch.setattr("app.services.google_auth_service.settings.google_client_id", "google-client")
    monkeypatch.setattr(
        "app.services.google_auth_service.id_token.verify_oauth2_token",
        lambda token, request, audience: {
            "sub": "google-sub",
            "email": "User@Example.com",
            "email_verified": True,
            "name": "Google User",
            "picture": "https://example.com/avatar.jpg",
        },
    )
    session = _Session(results=[None, None])

    tokens, user = await GoogleAuthService(session).login_with_google("valid-google-token")

    assert user.email == "user@example.com"
    assert user.google_id == "google-sub"
    assert user.auth_provider == "google"
    assert user.avatar_url == "https://example.com/avatar.jpg"
    assert user.is_verified is True
    assert user.onboarding_state == "new"
    assert tokens.access_token
    assert any(isinstance(item, UserProfile) for item in session.added)
    assert next(item for item in session.added if isinstance(item, UserProfile)).avatar_url == "https://example.com/avatar.jpg"
    assert any(isinstance(item, RefreshToken) for item in session.added)


@pytest.mark.asyncio
async def test_google_login_links_existing_email_without_duplicate_user(monkeypatch):
    existing = User(
        id=uuid4(),
        email="user@example.com",
        password_hash=hash_password("correct-password"),
        auth_provider="email",
        is_active=True,
        is_verified=False,
    )
    monkeypatch.setattr("app.services.google_auth_service.settings.google_client_id", "google-client")
    monkeypatch.setattr(
        "app.services.google_auth_service.id_token.verify_oauth2_token",
        lambda token, request, audience: {
            "sub": "google-sub",
            "email": "user@example.com",
            "email_verified": True,
            "name": "Google User",
            "picture": "https://example.com/google-avatar.jpg",
        },
    )
    session = _Session(results=[None, existing, None])

    tokens, user = await GoogleAuthService(session).login_with_google("valid-google-token")

    assert user is existing
    assert existing.google_id == "google-sub"
    assert existing.auth_provider == "google"
    assert existing.avatar_url == "https://example.com/google-avatar.jpg"
    assert existing.is_verified is True
    assert tokens.refresh_token
    assert len([item for item in session.added if isinstance(item, User)]) == 0


@pytest.mark.asyncio
async def test_google_login_rejects_unverified_google_email(monkeypatch):
    monkeypatch.setattr("app.services.google_auth_service.settings.google_client_id", "google-client")
    monkeypatch.setattr(
        "app.services.google_auth_service.id_token.verify_oauth2_token",
        lambda token, request, audience: {
            "sub": "google-sub",
            "email": "user@example.com",
            "email_verified": False,
            "name": "Google User",
        },
    )

    with pytest.raises(AppError) as exc_info:
        await GoogleAuthService(_Session()).login_with_google("valid-google-token")

    assert exc_info.value.status_code == 401
