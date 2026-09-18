from __future__ import annotations

import base64
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.connected_app import ConnectedAppAccount, NotionResource
from app.models.learning import LearningObservation
from app.models.user import User
from app.services.connected_apps.connected_app_action_service import ConnectedAppActionPreparationService
from app.services.connected_apps.oauth_lifecycle import ConnectedAppOAuthLifecycle

PROVIDER = "notion"
AUTHORIZE_URL = "https://api.notion.com/v1/oauth/authorize"
TOKEN_URL = "https://api.notion.com/v1/oauth/token"
API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2026-03-11"
SCOPES = ["read_workspace_metadata", "read_page_and_database_metadata"]
logger = logging.getLogger(__name__)


@dataclass
class NotionSyncResult:
    synced: int = 0
    updated: int = 0
    cancelled: int = 0
    observations: int = 0
    status: str = "connected"


class NotionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self.oauth = ConnectedAppOAuthLifecycle(session)

    async def status(self, user_id: UUID) -> dict:
        return self._status_out(await self.oauth.account(user_id, PROVIDER))

    async def authorization_url(self, user: User) -> dict:
        self._require_config()
        account = await self.oauth.ensure_account(user.id, PROVIDER, SCOPES)
        account.status = "connecting"
        account.last_error_code = None
        account.last_error_message = None
        state = self._encode_state(user.id)
        await self.oauth.store_state_nonce(account, self._state_nonce(state))
        params = {
            "client_id": self.settings.notion_client_id,
            "redirect_uri": self._redirect_uri(),
            "response_type": "code",
            "owner": "user",
            "state": state,
        }
        return {"authorizationUrl": f"{AUTHORIZE_URL}?{urlencode(params)}"}

    async def handle_callback(self, code: str | None, state: str | None, error: str | None, expected_user_id: UUID | None = None) -> str:
        frontend = self.settings.frontend_url.rstrip("/")
        user_id = self._decode_state(state or "")
        if expected_user_id is not None and user_id != expected_user_id:
            raise AppError("Invalid Notion OAuth state", status_code=400, code="invalid_oauth_state")
        account = await self.oauth.ensure_account(user_id, PROVIDER, SCOPES)
        await self.oauth.consume_state_nonce(account, self._state_nonce(state or ""), "Notion")
        if error:
            await self._set_error(account, "oauth_cancelled", "Notion connection was cancelled.")
            return f"{frontend}/connected?notion=cancelled"
        if not code:
            await self._set_error(account, "oauth_missing_code", "Notion did not return an authorization code.")
            return f"{frontend}/connected?notion=error"
        try:
            tokens = await self._exchange_code(code)
            access = str(tokens.get("access_token") or "")
            if not access:
                raise AppError("Notion did not return an access token", status_code=400, code="missing_access_token")
            account.encrypted_access_token = self.oauth.encrypt(access)
            refresh = str(tokens.get("refresh_token") or "")
            account.encrypted_refresh_token = self.oauth.encrypt(refresh) if refresh else None
            account.access_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(60, int(tokens.get("expires_in") or 315_360_000) - 60))
            account.scopes = SCOPES
            owner = ((tokens.get("owner") or {}).get("user") or {})
            account.provider_account_id = str(tokens.get("workspace_id") or "")[:240] or None
            account.app_metadata = {
                **(account.app_metadata or {}),
                "workspace_id": str(tokens.get("workspace_id") or ""),
                "workspace_name": str(tokens.get("workspace_name") or "")[:300],
                "workspace_icon": str(tokens.get("workspace_icon") or "")[:500],
                "owner_name": str(owner.get("name") or "")[:300],
            }
            account.status = "connected"
            account.last_error_code = None
            account.last_error_message = None
            await self.session.flush()
            await self.sync(user_id)
            return f"{frontend}/connected?notion=connected"
        except AppError as exc:
            await self._set_error(account, exc.code or "oauth_exchange_failed", exc.user_message or "Notion could not connect.")
            return f"{frontend}/connected?notion=error"

    async def sync(self, user_id: UUID) -> NotionSyncResult:
        account = await self.oauth.required_account(user_id, PROVIDER)
        if not account.encrypted_access_token:
            await self._set_error(account, "permission_revoked", "Notion needs to be reconnected.", "permission_revoked")
            return NotionSyncResult(status="permission_revoked")
        account.status = "syncing"
        await self.session.flush()
        try:
            access = await self._access_token(account)
            result = await self._sync_resources(account, access)
            result.observations = await self._create_observations(account)
            if result.observations:
                await ConnectedAppActionPreparationService(self.session).prepare_for_provider(
                    user_id=account.user_id,
                    provider=PROVIDER,
                    observations_created=result.observations,
                    account_metadata=account.app_metadata,
                )
            account.status = "connected"
            account.last_synced_at = datetime.now(timezone.utc)
            account.last_error_code = None
            account.last_error_message = None
            await self.session.flush()
            return result
        except AppError as exc:
            status = "permission_revoked" if exc.code in {"permission_revoked", "token_expired"} else "error"
            await self._set_error(account, exc.code or "sync_failed", exc.user_message or "Notion sync failed.", status)
            return NotionSyncResult(status=status)

    async def disconnect(self, user_id: UUID) -> dict:
        account = await self.oauth.required_account(user_id, PROVIDER)
        token = self.oauth.try_decrypt(account.encrypted_access_token)
        if token and self.settings.notion_client_id and self.settings.notion_client_secret:
            credentials = base64.b64encode(f"{self.settings.notion_client_id}:{self.settings.notion_client_secret}".encode()).decode()
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(f"{API_URL}/oauth/revoke", headers={"Authorization": f"Basic {credentials}", "Notion-Version": NOTION_VERSION, "Content-Type": "application/json"}, json={"token": token})
            except Exception:
                logger.warning("Notion remote token revocation did not complete user_id=%s", user_id)
        self.oauth.clear_tokens(account)
        await self.session.flush()
        return self._status_out(account)

    async def sync_if_due(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
        accounts = list((await self.session.execute(select(ConnectedAppAccount).where(ConnectedAppAccount.provider == PROVIDER, ConnectedAppAccount.status.in_(("connected", "error"))))).scalars())
        synced = 0
        for account in accounts:
            last_sync = self._aware(account.last_synced_at) if account.last_synced_at else None
            if last_sync and last_sync >= cutoff:
                continue
            try:
                result = await self.sync(account.user_id)
                synced += int(result.status == "connected")
            except Exception:
                logger.exception("Scheduled Notion sync failed user_id=%s", account.user_id)
        return synced

    async def _sync_resources(self, account: ConnectedAppAccount, access: str) -> NotionSyncResult:
        result = NotionSyncResult()
        watermark = self._datetime(account.sync_token)
        rows = await self._search(access, watermark)
        ids = [str(row.get("id") or "") for row in rows if row.get("id")]
        existing = {row.provider_resource_id: row for row in (await self.session.execute(select(NotionResource).where(NotionResource.user_id == account.user_id, NotionResource.provider_resource_id.in_(ids)))).scalars()} if ids else {}
        newest = watermark
        for raw in rows:
            provider_id = str(raw.get("id") or "")
            if not provider_id:
                continue
            resource = existing.get(provider_id)
            created = resource is None
            if resource is None:
                resource = NotionResource(user_id=account.user_id, connected_account_id=account.id, provider_resource_id=provider_id)
                self.session.add(resource)
                existing[provider_id] = resource
            edited = self._datetime(raw.get("last_edited_time"))
            parent = raw.get("parent") or {}
            parent_type = str(parent.get("type") or "workspace")
            resource.resource_type = "database" if raw.get("object") in {"database", "data_source"} else "page"
            resource.title = self._title(raw)[:500]
            resource.parent_type = parent_type[:80]
            resource.parent_provider_id = str(parent.get(parent_type) or "")[:128]
            resource.provider_created_at = self._datetime(raw.get("created_time"))
            resource.provider_edited_at = edited
            resource.archived = bool(raw.get("archived") or raw.get("in_trash"))
            resource.resource_metadata = {
                "propertyCount": len(raw.get("properties") or {}),
                "public": bool(raw.get("public_url")),
            }
            result.cancelled += int(resource.archived)
            result.synced += int(created and not resource.archived)
            result.updated += int(not created and not resource.archived)
            if edited and (not newest or edited > newest):
                newest = edited
        if newest:
            account.sync_token = self._rfc3339(newest)
        recent_cutoff = datetime.now(timezone.utc) - timedelta(days=14)
        active = list((await self.session.execute(select(NotionResource).where(NotionResource.user_id == account.user_id, NotionResource.archived.is_(False)))).scalars())
        account.app_metadata = {
            **(account.app_metadata or {}),
            "pages_count": sum(row.resource_type == "page" for row in active),
            "databases_count": sum(row.resource_type == "database" for row in active),
            "recently_edited_count": sum(bool(row.provider_edited_at and self._aware(row.provider_edited_at) >= recent_cutoff) for row in active),
            "stale_resource_count": sum(bool(row.provider_edited_at and self._aware(row.provider_edited_at) < datetime.now(timezone.utc) - timedelta(days=45)) for row in active),
        }
        return result

    async def _search(self, access: str, watermark: datetime | None) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        cursor: str | None = None
        headers = self._headers(access)
        async with httpx.AsyncClient(timeout=25) as client:
            while True:
                body: dict[str, Any] = {"page_size": 100, "sort": {"direction": "descending", "timestamp": "last_edited_time"}}
                if cursor:
                    body["start_cursor"] = cursor
                response = await client.post(f"{API_URL}/search", headers=headers, json=body)
                self._raise_api(response)
                payload = response.json()
                page = payload.get("results") or []
                for raw in page:
                    edited = self._datetime(raw.get("last_edited_time"))
                    if watermark and edited and edited <= watermark:
                        return rows
                    rows.append(raw)
                if not payload.get("has_more") or not payload.get("next_cursor"):
                    return rows
                cursor = str(payload["next_cursor"])

    async def _create_observations(self, account: ConnectedAppAccount) -> int:
        now = datetime.now(timezone.utc)
        resources = list((await self.session.execute(select(NotionResource).where(NotionResource.user_id == account.user_id, NotionResource.archived.is_(False)))).scalars())
        recent = [row for row in resources if row.provider_edited_at and self._aware(row.provider_edited_at) >= now - timedelta(days=14)]
        values: list[str] = []
        if recent:
            values.append(f"Notion evidence: {len(recent)} page{'s or databases were' if len(recent) != 1 else ' or database was'} edited in the last 14 days, indicating active knowledge work.")
        for row in recent[:5]:
            if row.title and any(term in row.title.casefold() for term in ("project", "roadmap", "plan", "research")):
                values.append(f"Notion evidence: “{row.title}” was recently updated and may reflect an active project or research thread.")
            if row.title and any(term in row.title.casefold() for term in ("meeting", "notes", "retro")):
                values.append(f"Notion evidence: “{row.title}” was recently updated and may contain follow-up context worth reviewing.")
        stale = [row for row in resources if row.provider_edited_at and self._aware(row.provider_edited_at) < now - timedelta(days=45)]
        if stale:
            values.append(f"Notion evidence: {len(stale)} knowledge item{'s have' if len(stale) != 1 else ' has'} not been updated for at least 45 days.")
        existing = {row.content for row in (await self.session.execute(select(LearningObservation).where(LearningObservation.user_id == account.user_id, LearningObservation.source == PROVIDER))).scalars()}
        created = 0
        for content in values:
            if content not in existing:
                self.session.add(LearningObservation(user_id=account.user_id, source=PROVIDER, content=content, status="observed"))
                created += 1
        await self.session.flush()
        return created

    async def _exchange_code(self, code: str) -> dict[str, Any]:
        credentials = base64.b64encode(f"{self.settings.notion_client_id}:{self.settings.notion_client_secret}".encode()).decode()
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(TOKEN_URL, headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/json"}, json={"grant_type": "authorization_code", "code": code, "redirect_uri": self._redirect_uri()})
        if response.status_code >= 400:
            raise AppError("Notion OAuth exchange failed", status_code=400, code="oauth_exchange_failed", user_message="Notion could not complete authorization.")
        return response.json()

    async def _access_token(self, account: ConnectedAppAccount) -> str:
        now = datetime.now(timezone.utc)
        expires = self._aware(account.access_token_expires_at) if account.access_token_expires_at else None
        if account.encrypted_access_token and (not expires or expires > now + timedelta(minutes=2)):
            return self.oauth.decrypt(account.encrypted_access_token)
        refresh = self.oauth.try_decrypt(account.encrypted_refresh_token)
        if not refresh:
            if account.encrypted_access_token:
                return self.oauth.decrypt(account.encrypted_access_token)
            raise AppError("Notion authorization expired", status_code=409, code="token_expired", user_message="Reconnect Notion to continue syncing.")
        credentials = base64.b64encode(f"{self.settings.notion_client_id}:{self.settings.notion_client_secret}".encode()).decode()
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(TOKEN_URL, headers={"Authorization": f"Basic {credentials}", "Notion-Version": NOTION_VERSION, "Content-Type": "application/json"}, json={"grant_type": "refresh_token", "refresh_token": refresh})
        if response.status_code >= 400:
            raise AppError("Notion permission was revoked", status_code=409, code="permission_revoked", user_message="Notion authorization expired or was removed. Reconnect to continue.")
        tokens = response.json()
        access = str(tokens.get("access_token") or "")
        if not access:
            raise AppError("Notion refresh did not return an access token", status_code=409, code="token_expired", user_message="Reconnect Notion to continue syncing.")
        account.encrypted_access_token = self.oauth.encrypt(access)
        if tokens.get("refresh_token"):
            account.encrypted_refresh_token = self.oauth.encrypt(str(tokens["refresh_token"]))
        account.access_token_expires_at = now + timedelta(seconds=max(60, int(tokens.get("expires_in") or 315_360_000) - 60))
        return access

    async def _set_error(self, account: ConnectedAppAccount, code: str, message: str, status: str = "error") -> None:
        account.status = status
        account.last_error_code = code
        account.last_error_message = message
        await self.session.flush()

    def _status_out(self, account: ConnectedAppAccount | None) -> dict:
        status = account.status if account else "not_connected"
        return {
            "provider": PROVIDER,
            "status": status,
            "connected": status == "connected",
            "lastSyncedAt": account.last_synced_at if account else None,
            "lastErrorCode": account.last_error_code if account else None,
            "lastErrorMessage": account.last_error_message if account else None,
            "permissions": ["Read selected workspace page, database, hierarchy, and edit metadata"] if account else [],
            "scopes": account.scopes if account else [],
            "privacy": {
                "why": "Notion helps Synzept understand projects, documentation, planning, and knowledge momentum.",
                "reads": "Titles, parent hierarchy, last-edited timestamps, workspace metadata, and page or database metadata from the selected workspace.",
                "usage": "Knowledge evidence becomes an observation and requires approval before changing understanding. Page content is not stored.",
                "ignored": "Synzept cannot edit, create, delete, archive, restore, or share Notion content.",
            },
        }

    def _encode_state(self, user_id: UUID) -> str:
        return jwt.encode({"sub": str(user_id), "provider": PROVIDER, "nonce": secrets.token_urlsafe(12), "exp": datetime.now(timezone.utc) + timedelta(minutes=15), "type": "notion_oauth_state"}, self.settings.jwt_secret_key, algorithm=self.settings.jwt_algorithm)

    def _decode_state(self, state: str) -> UUID:
        try:
            payload = jwt.decode(state, self.settings.jwt_secret_key, algorithms=[self.settings.jwt_algorithm])
            if payload.get("type") != "notion_oauth_state" or payload.get("provider") != PROVIDER:
                raise ValueError
            return UUID(str(payload["sub"]))
        except (JWTError, ValueError, KeyError) as exc:
            raise AppError("Invalid Notion OAuth state", status_code=400, code="invalid_oauth_state") from exc

    def _state_nonce(self, state: str) -> str:
        try:
            payload = jwt.decode(state, self.settings.jwt_secret_key, algorithms=[self.settings.jwt_algorithm])
            return str(payload["nonce"])
        except (JWTError, KeyError, TypeError) as exc:
            raise AppError("Invalid Notion OAuth state", status_code=400, code="invalid_oauth_state") from exc

    def _require_config(self) -> None:
        if not self.settings.notion_client_id or not self.settings.notion_client_secret:
            raise AppError("Notion is not configured", status_code=503, code="notion_not_configured", user_message="Notion is not configured for this Synzept environment yet.")

    def _redirect_uri(self) -> str:
        return self.settings.notion_redirect_uri or f"{self.settings.frontend_url.rstrip('/').replace('localhost:3000', 'localhost:8000')}/api/connected-apps/notion/callback"

    @staticmethod
    def _headers(access: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {access}", "Notion-Version": NOTION_VERSION, "Content-Type": "application/json"}

    @staticmethod
    def _raise_api(response: httpx.Response) -> None:
        if response.status_code in {401, 403}:
            raise AppError("Notion permission expired", status_code=409, code="permission_revoked", user_message="Notion authorization expired or access was removed. Reconnect to continue.")
        if response.status_code == 429:
            raise AppError("Notion rate limit reached", status_code=429, code="notion_rate_limited", user_message="Notion asked Synzept to slow down. Sync again shortly.")
        if response.status_code >= 500:
            raise AppError("Notion unavailable", status_code=503, code="notion_unavailable", user_message="Notion is unavailable right now.")
        if response.status_code >= 400:
            raise AppError("Notion sync failed", status_code=400, code="sync_failed", user_message="Notion sync failed.")

    @staticmethod
    def _title(raw: dict[str, Any]) -> str:
        if raw.get("object") in {"database", "data_source"}:
            return "".join(str(item.get("plain_text") or "") for item in raw.get("title") or []).strip() or "Untitled database"
        for value in (raw.get("properties") or {}).values():
            if value.get("type") == "title":
                return "".join(str(item.get("plain_text") or "") for item in value.get("title") or []).strip() or "Untitled page"
        return "Untitled page"

    @staticmethod
    def _datetime(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _rfc3339(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
