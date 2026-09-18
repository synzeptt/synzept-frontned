from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError
from app.models.connected_app import ConnectedAppAccount


class ConnectedAppOAuthLifecycle:
    """Shared token vault and account lifecycle for OAuth connected apps."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def account(self, user_id: UUID, provider: str) -> ConnectedAppAccount | None:
        result = await self.session.execute(
            select(ConnectedAppAccount).where(
                ConnectedAppAccount.user_id == user_id,
                ConnectedAppAccount.provider == provider,
            )
        )
        return result.scalar_one_or_none()

    async def ensure_account(self, user_id: UUID, provider: str, scopes: list[str]) -> ConnectedAppAccount:
        account = await self.account(user_id, provider)
        if account:
            return account
        account = ConnectedAppAccount(user_id=user_id, provider=provider, status="connecting", scopes=scopes)
        self.session.add(account)
        await self.session.flush()
        return account

    async def store_state_nonce(self, account: ConnectedAppAccount, nonce: str) -> None:
        account.app_metadata = {**(account.app_metadata or {}), "oauth_state_nonce": nonce}
        await self.session.flush()

    async def consume_state_nonce(self, account: ConnectedAppAccount, nonce: str, label: str) -> None:
        result = await self.session.execute(
            select(ConnectedAppAccount).where(ConnectedAppAccount.id == account.id).with_for_update()
        )
        locked_account = result.scalar_one()
        if (locked_account.app_metadata or {}).get("oauth_state_nonce") != nonce:
            raise AppError(
                f"Invalid {label} OAuth state",
                status_code=400,
                code="invalid_oauth_state",
                user_message=f"The {label} connection could not be verified. Start the connection again.",
            )
        metadata = dict(locked_account.app_metadata or {})
        metadata.pop("oauth_state_nonce", None)
        locked_account.app_metadata = metadata
        await self.session.flush()

    async def required_account(self, user_id: UUID, provider: str) -> ConnectedAppAccount:
        account = await self.account(user_id, provider)
        if not account or account.status == "not_connected":
            raise NotFoundError(f"{provider} is not connected")
        return account

    def encrypt(self, value: str) -> str:
        return self._fernet().encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        try:
            return self._fernet().decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise AppError(
                "Stored connected-app token could not be decrypted",
                status_code=409,
                code="token_expired",
                user_message="Reconnect this provider to refresh authorization.",
            ) from exc

    def try_decrypt(self, value: str | None) -> str | None:
        if not value:
            return None
        try:
            return self.decrypt(value)
        except AppError:
            return None

    async def access_token(
        self,
        account: ConnectedAppAccount,
        *,
        label: str,
        token_url: str,
        client_id: str,
        client_secret: str,
        extra_data: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        success_field: str | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        if account.encrypted_access_token and account.access_token_expires_at:
            expires = account.access_token_expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires > now + timedelta(minutes=2):
                return self.decrypt(account.encrypted_access_token)
        refresh = self.decrypt(account.encrypted_refresh_token or "")
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh,
            "grant_type": "refresh_token",
            **(extra_data or {}),
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(token_url, data=data, **({"headers": headers} if headers else {}))
        except httpx.TimeoutException as exc:
            raise AppError(f"{label} token refresh timed out", status_code=504, code="provider_timeout", user_message=f"{label} is taking too long to respond. Try again.") from exc
        except httpx.RequestError as exc:
            raise AppError(f"{label} token refresh failed", status_code=503, code="provider_unavailable", user_message=f"{label} is unavailable right now. Try again later.") from exc
        if response.status_code in {400, 401}:
            raise AppError(
                f"{label} permission was revoked",
                status_code=409,
                code="permission_revoked",
                user_message=f"{label} permission expired or was revoked. Reconnect to resume sync.",
            )
        if response.status_code >= 500:
            raise AppError(f"{label} token refresh failed", status_code=503, code="provider_unavailable", user_message=f"{label} is unavailable right now.")
        if response.status_code >= 400:
            raise AppError(f"{label} token refresh failed", status_code=400, code="token_expired", user_message=f"{label} authorization expired. Reconnect.")
        tokens = response.json()
        if success_field and not tokens.get(success_field):
            raise AppError(
                f"{label} token refresh failed: {tokens.get('error') or 'provider rejected refresh'}",
                status_code=409,
                code="permission_revoked",
                user_message=f"{label} permission expired or was revoked. Reconnect to resume sync.",
            )
        access = str(tokens["access_token"])
        account.encrypted_access_token = self.encrypt(access)
        if tokens.get("refresh_token"):
            account.encrypted_refresh_token = self.encrypt(str(tokens["refresh_token"]))
        account.access_token_expires_at = now + timedelta(seconds=int(tokens.get("expires_in") or 3600) - 60)
        return access

    async def revoke(self, account: ConnectedAppAccount, revoke_url: str, *, token_in_body: bool = False) -> None:
        token = self.try_decrypt(account.encrypted_refresh_token) or self.try_decrypt(account.encrypted_access_token)
        if not token:
            return
        async with httpx.AsyncClient(timeout=10) as client:
            if token_in_body:
                await client.post(revoke_url, data={"token": token})
            else:
                await client.post(revoke_url, params={"token": token})

    def clear_tokens(self, account: ConnectedAppAccount) -> None:
        account.status = "not_connected"
        account.encrypted_refresh_token = None
        account.encrypted_access_token = None
        account.access_token_expires_at = None
        account.sync_token = None
        account.last_error_code = None
        account.last_error_message = None

    async def refresh(self, account: ConnectedAppAccount, *, label: str, token_url: str, client_id: str, client_secret: str) -> str:
        """Refresh and persist an access token using the encrypted refresh token."""
        return await self.access_token(account, label=label, token_url=token_url, client_id=client_id, client_secret=client_secret)

    async def disconnect(self, account: ConnectedAppAccount, *, revoke_url: str) -> None:
        try:
            await self.revoke(account, revoke_url)
        except httpx.RequestError:
            pass
        self.clear_tokens(account)
        await self.session.flush()

    async def reconnect(self, user_id: UUID, provider: str, scopes: list[str]) -> ConnectedAppAccount:
        account = await self.ensure_account(user_id, provider, scopes)
        self.clear_tokens(account)
        account.status = "connecting"
        account.scopes = scopes
        await self.session.flush()
        return account

    def validate_scopes(self, account: ConnectedAppAccount, required_scopes: list[str]) -> list[str]:
        granted = set(account.scopes or [])
        return [scope for scope in required_scopes if scope not in granted]

    def health(self, account: ConnectedAppAccount | None, required_scopes: list[str] | None = None) -> dict[str, object]:
        if account is None or account.status in {"not_connected", "connecting"}:
            return {"status": "disconnected", "connected": False, "missing_scopes": list(required_scopes or [])}
        missing = self.validate_scopes(account, required_scopes or [])
        if missing:
            return {"status": "permission_missing", "connected": True, "missing_scopes": missing}
        if account.status == "error" and account.last_error_code in {"permission_revoked", "token_expired"}:
            return {"status": "token_expired", "connected": False, "missing_scopes": []}
        return {"status": "connected", "connected": True, "missing_scopes": []}

    def _fernet(self) -> Fernet:
        secret = self.settings.connected_app_token_secret
        if not secret:
            raise AppError(
                "Connected-app encryption is not configured",
                status_code=503,
                code="app_error",
                user_message="Connected apps are temporarily unavailable. Please try again later.",
            )
        digest = hashlib.sha256(secret.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(digest))



OAuthManager = ConnectedAppOAuthLifecycle
