from __future__ import annotations

import logging
import re
import secrets
from collections import Counter
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
from app.models.connected_app import ConnectedAppAccount, SlackChannel, SlackConversationActivity, SlackUser
from app.models.learning import LearningObservation
from app.models.user import User
from app.services.connected_apps.connected_app_action_service import ConnectedAppActionPreparationService
from app.services.connected_apps.oauth_lifecycle import ConnectedAppOAuthLifecycle

PROVIDER = "slack"
AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
TOKEN_URL = "https://slack.com/api/oauth.v2.access"
API_URL = "https://slack.com/api"
SCOPES = [
    "team:read",
    "channels:read",
    "groups:read",
    "im:read",
    "mpim:read",
    "users:read",
    "channels:history",
    "groups:history",
    "im:history",
    "mpim:history",
]
MENTION_PATTERN = re.compile(r"<@([A-Z0-9]+)(?:\|[^>]+)?>")
BLOCKER_PATTERN = re.compile(r"\b(blocked|blocker|blocking|waiting on|waiting for|stuck on)\b", re.IGNORECASE)
DECISION_PATTERN = re.compile(r"\b(decision pending|needs? a decision|awaiting (?:a )?decision|yet to decide|need to decide)\b", re.IGNORECASE)
logger = logging.getLogger(__name__)


@dataclass
class SlackSyncResult:
    synced: int = 0
    updated: int = 0
    cancelled: int = 0
    observations: int = 0
    status: str = "connected"


class SlackService:
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
            "client_id": self.settings.slack_client_id,
            "redirect_uri": self._redirect_uri(),
            "scope": ",".join(SCOPES),
            "state": state,
        }
        return {"authorizationUrl": f"{AUTHORIZE_URL}?{urlencode(params)}"}

    async def handle_callback(self, code: str | None, state: str | None, error: str | None, expected_user_id: UUID | None = None) -> str:
        frontend = self.settings.frontend_url.rstrip("/")
        user_id = self._decode_state(state or "")
        if expected_user_id is not None and user_id != expected_user_id:
            raise AppError("Invalid Slack OAuth state", status_code=400, code="invalid_oauth_state")
        account = await self.oauth.ensure_account(user_id, PROVIDER, SCOPES)
        await self.oauth.consume_state_nonce(account, self._state_nonce(state or ""), "Slack")
        if error:
            await self._set_error(account, "oauth_cancelled", "Slack connection was cancelled.")
            return f"{frontend}/connected?slack=cancelled"
        if not code:
            await self._set_error(account, "oauth_missing_code", "Slack did not return an authorization code.")
            return f"{frontend}/connected?slack=error"
        try:
            tokens = await self._exchange_code(code)
            access = str(tokens.get("access_token") or "")
            if not access:
                raise AppError("Slack did not return an access token", status_code=400, code="missing_access_token")
            account.encrypted_access_token = self.oauth.encrypt(access)
            refresh = tokens.get("refresh_token")
            account.encrypted_refresh_token = self.oauth.encrypt(str(refresh)) if refresh else None
            expires_in = int(tokens.get("expires_in") or 31_536_000)
            account.access_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(60, expires_in - 60))
            account.scopes = SCOPES
            team = tokens.get("team") or {}
            account.provider_account_id = str(team.get("id") or "")[:240] or None
            account.app_metadata = {
                **(account.app_metadata or {}),
                "workspace_id": str(team.get("id") or ""),
                "workspace_name": str(team.get("name") or "")[:300],
                "authed_user_id": str((tokens.get("authed_user") or {}).get("id") or ""),
                "bot_user_id": str(tokens.get("bot_user_id") or ""),
            }
            account.status = "connected"
            account.last_error_code = None
            account.last_error_message = None
            await self.session.flush()
            await self.sync(user_id)
            return f"{frontend}/connected?slack=connected"
        except AppError as exc:
            await self._set_error(account, exc.code or "oauth_exchange_failed", exc.user_message or "Slack could not connect.")
            return f"{frontend}/connected?slack=error"

    async def sync(self, user_id: UUID) -> SlackSyncResult:
        account = await self.oauth.required_account(user_id, PROVIDER)
        if not account.encrypted_access_token and not account.encrypted_refresh_token:
            await self._set_error(account, "permission_revoked", "Slack needs to be reconnected.", "permission_revoked")
            return SlackSyncResult(status="permission_revoked")
        account.status = "syncing"
        await self.session.flush()
        try:
            access = await self._access_token(account)
            result = await self._sync_collaboration(account, access)
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
            await self._set_error(account, exc.code or "sync_failed", exc.user_message or "Slack sync failed.", status)
            return SlackSyncResult(status=status)

    async def disconnect(self, user_id: UUID) -> dict:
        account = await self.oauth.required_account(user_id, PROVIDER)
        access = self.oauth.try_decrypt(account.encrypted_access_token)
        if access:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(f"{API_URL}/auth.revoke", headers=self._headers(access))
            except Exception:
                logger.warning("Slack remote token revocation did not complete user_id=%s", user_id)
        self.oauth.clear_tokens(account)
        await self.session.flush()
        return self._status_out(account)

    async def sync_if_due(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
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
                logger.exception("Scheduled Slack sync failed user_id=%s", account.user_id)
        return synced

    async def _sync_collaboration(self, account: ConnectedAppAccount, access: str) -> SlackSyncResult:
        metadata = account.app_metadata or {}
        result = SlackSyncResult()
        async with httpx.AsyncClient(timeout=25) as client:
            team = await self._api(client, "team.info", access)
            team_info = team.get("team") or {}
            account.provider_account_id = str(team_info.get("id") or account.provider_account_id or "")[:240] or None
            users_payload = await self._paginated(client, "users.list", access, "members")
            raw_channels = await self._paginated(
                client,
                "conversations.list",
                access,
                "channels",
                {"types": "public_channel,private_channel,im,mpim", "exclude_archived": "true"},
            )
            users = await self._upsert_users(account, users_payload)
            channels, channel_created, channel_updated = await self._upsert_channels(account, raw_channels, users)
            result.synced += channel_created
            result.updated += channel_updated
            watermarks = dict(metadata.get("channel_watermarks") or {})
            initial_oldest = str((datetime.now(timezone.utc) - timedelta(days=30)).timestamp())
            for channel in channels:
                if channel.is_archived or not (channel.is_member or channel.channel_type in {"im", "mpim"}):
                    continue
                messages = await self._paginated(
                    client,
                    "conversations.history",
                    access,
                    "messages",
                    {"channel": channel.provider_channel_id, "oldest": str(watermarks.get(channel.provider_channel_id) or initial_oldest), "inclusive": "false"},
                )
                created, updated, newest = await self._upsert_activities(account, channel, messages)
                result.synced += created
                result.updated += updated
                if newest:
                    watermarks[channel.provider_channel_id] = newest
        await self.session.flush()
        now = datetime.now(timezone.utc)
        recent = list((await self.session.execute(select(SlackConversationActivity).where(SlackConversationActivity.user_id == account.user_id, SlackConversationActivity.occurred_at >= now - timedelta(days=7)))).scalars())
        account.app_metadata = {
            **metadata,
            "workspace_id": str(team_info.get("id") or metadata.get("workspace_id") or ""),
            "workspace_name": str(team_info.get("name") or metadata.get("workspace_name") or "")[:300],
            "channel_watermarks": watermarks,
            "joined_channels_count": sum(1 for row in channels if row.is_member and row.channel_type == "channel"),
            "recent_activity_count": len(recent),
            "recent_thread_count": len({row.thread_ts for row in recent if row.thread_ts}),
            "direct_mention_count": sum(1 for row in recent if str(metadata.get("authed_user_id") or "") in (row.mention_user_ids or [])),
            "blocker_signal_count": sum(1 for row in recent if "blocker" in (row.signal_types or [])),
            "decision_pending_count": sum(1 for row in recent if "decision_pending" in (row.signal_types or [])),
            "recent_collaborator_count": len({person for row in recent for person in (row.participant_user_ids or [])}),
        }
        return result

    async def _upsert_users(self, account: ConnectedAppAccount, payload: list[dict[str, Any]]) -> dict[str, SlackUser]:
        existing = {row.provider_user_id: row for row in (await self.session.execute(select(SlackUser).where(SlackUser.user_id == account.user_id))).scalars()}
        for raw in payload:
            provider_id = str(raw.get("id") or "")
            if not provider_id:
                continue
            user = existing.get(provider_id)
            if user is None:
                user = SlackUser(user_id=account.user_id, connected_account_id=account.id, provider_user_id=provider_id)
                self.session.add(user)
                existing[provider_id] = user
            profile = raw.get("profile") or {}
            user.display_name = str(profile.get("display_name") or profile.get("real_name") or raw.get("real_name") or "")[:300]
            user.real_name = str(profile.get("real_name") or raw.get("real_name") or "")[:300]
            user.title = str(profile.get("title") or "")[:300]
            user.is_bot = bool(raw.get("is_bot"))
            user.deleted = bool(raw.get("deleted"))
        await self.session.flush()
        return existing

    async def _upsert_channels(self, account: ConnectedAppAccount, payload: list[dict[str, Any]], users: dict[str, SlackUser]) -> tuple[list[SlackChannel], int, int]:
        existing = {row.provider_channel_id: row for row in (await self.session.execute(select(SlackChannel).where(SlackChannel.user_id == account.user_id))).scalars()}
        created = updated = 0
        for raw in payload:
            provider_id = str(raw.get("id") or "")
            if not provider_id:
                continue
            channel = existing.get(provider_id)
            is_new = channel is None
            if channel is None:
                channel = SlackChannel(user_id=account.user_id, connected_account_id=account.id, provider_channel_id=provider_id)
                self.session.add(channel)
                existing[provider_id] = channel
            channel_type = "im" if raw.get("is_im") else "mpim" if raw.get("is_mpim") else "channel"
            peer = users.get(str(raw.get("user") or ""))
            channel.name = str(raw.get("name") or (f"Direct message with {peer.display_name}" if peer else "Direct message"))[:300]
            channel.channel_type = channel_type
            channel.is_private = bool(raw.get("is_private") or channel_type in {"im", "mpim"})
            channel.is_member = bool(raw.get("is_member") or channel_type in {"im", "mpim"})
            channel.is_archived = bool(raw.get("is_archived"))
            channel.member_count = int(raw.get("num_members") or 0)
            created += int(is_new)
            updated += int(not is_new)
        await self.session.flush()
        return list(existing.values()), created, updated

    async def _upsert_activities(self, account: ConnectedAppAccount, channel: SlackChannel, payload: list[dict[str, Any]]) -> tuple[int, int, str | None]:
        timestamps = [str(raw.get("ts") or "") for raw in payload if raw.get("ts")]
        if not timestamps:
            return 0, 0, None
        existing = {row.provider_message_ts: row for row in (await self.session.execute(select(SlackConversationActivity).where(SlackConversationActivity.channel_id == channel.id, SlackConversationActivity.provider_message_ts.in_(timestamps)))).scalars()}
        created = updated = 0
        newest: str | None = None
        for raw in payload:
            timestamp = str(raw.get("ts") or "")
            author = str(raw.get("user") or raw.get("bot_id") or "")
            if not timestamp or not author:
                continue
            activity = existing.get(timestamp)
            is_new = activity is None
            if activity is None:
                activity = SlackConversationActivity(user_id=account.user_id, connected_account_id=account.id, channel_id=channel.id, provider_message_ts=timestamp)
                self.session.add(activity)
                existing[timestamp] = activity
            text = str(raw.get("text") or "")
            mentions = list(dict.fromkeys(MENTION_PATTERN.findall(text)))
            signals = []
            if BLOCKER_PATTERN.search(text):
                signals.append("blocker")
            if DECISION_PATTERN.search(text):
                signals.append("decision_pending")
            participants = list(dict.fromkeys([author, *mentions, *[str(value) for value in (raw.get("reply_users") or []) if value]]))
            activity.author_provider_user_id = author[:128]
            activity.thread_ts = str(raw.get("thread_ts") or (timestamp if raw.get("reply_count") else ""))[:64]
            activity.reply_count = int(raw.get("reply_count") or 0)
            activity.mention_user_ids = mentions
            activity.participant_user_ids = participants
            activity.signal_types = signals
            activity.occurred_at = self._slack_datetime(timestamp)
            activity.is_direct = channel.channel_type in {"im", "mpim"}
            existing_activity_at = self._aware(channel.last_activity_at) if channel.last_activity_at else None
            channel.last_activity_at = max(filter(None, [existing_activity_at, activity.occurred_at]), default=None)
            created += int(is_new)
            updated += int(not is_new)
            newest = max(newest or timestamp, timestamp, key=lambda value: float(value))
        await self.session.flush()
        return created, updated, newest

    async def _create_observations(self, account: ConnectedAppAccount) -> int:
        now = datetime.now(timezone.utc)
        activities = list((await self.session.execute(select(SlackConversationActivity).where(SlackConversationActivity.user_id == account.user_id, SlackConversationActivity.occurred_at >= now - timedelta(days=14)))).scalars())
        channels = {row.id: row for row in (await self.session.execute(select(SlackChannel).where(SlackChannel.user_id == account.user_id))).scalars()}
        users = {row.provider_user_id: row for row in (await self.session.execute(select(SlackUser).where(SlackUser.user_id == account.user_id))).scalars()}
        observations: list[str] = []
        blocker_count = sum("blocker" in (row.signal_types or []) for row in activities)
        decision_count = sum("decision_pending" in (row.signal_types or []) for row in activities)
        if blocker_count:
            observations.append(f"Slack evidence: {blocker_count} recent message{'s' if blocker_count != 1 else ''} explicitly used blocker or waiting language.")
        if decision_count:
            observations.append(f"Slack evidence: {decision_count} recent message{'s' if decision_count != 1 else ''} explicitly indicated a pending decision.")
        collaborator_counts = Counter(person for row in activities for person in (row.participant_user_ids or []) if person not in {account.app_metadata.get("authed_user_id"), account.app_metadata.get("bot_user_id")})
        for provider_id, count in collaborator_counts.most_common(3):
            person = users.get(provider_id)
            if person and person.display_name and count >= 3:
                observations.append(f"Slack evidence: recent synced activity shows frequent collaboration with {person.display_name} ({count} conversation interactions).")
        engineering = [row for row in activities if any(term in (channels.get(row.channel_id).name.lower() if channels.get(row.channel_id) else "") for term in ("eng", "dev", "build", "release"))]
        if len(engineering) >= 5:
            observations.append(f"Slack evidence: {len(engineering)} recent activities in engineering-related channels indicate an active engineering discussion pattern.")
        direct_mentions = int((account.app_metadata or {}).get("direct_mention_count") or 0)
        if direct_mentions >= 10:
            observations.append(f"Slack evidence: {direct_mentions} direct mentions in recent synced activity indicate a high visible communication load.")
        existing = {row.content for row in (await self.session.execute(select(LearningObservation).where(LearningObservation.user_id == account.user_id, LearningObservation.source == PROVIDER))).scalars()}
        created = 0
        for content in observations:
            if content not in existing:
                self.session.add(LearningObservation(user_id=account.user_id, source=PROVIDER, content=content, status="observed"))
                created += 1
        await self.session.flush()
        return created

    async def _paginated(self, client: httpx.AsyncClient, method: str, access: str, collection: str, params: dict[str, str] | None = None) -> list[dict[str, Any]]:
        cursor = ""
        rows: list[dict[str, Any]] = []
        while True:
            payload = await self._api(client, method, access, {**(params or {}), "limit": "200", **({"cursor": cursor} if cursor else {})})
            rows.extend(payload.get(collection) or [])
            cursor = str(((payload.get("response_metadata") or {}).get("next_cursor") or "")).strip()
            if not cursor:
                return rows

    async def _api(self, client: httpx.AsyncClient, method: str, access: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        response = await client.get(f"{API_URL}/{method}", headers=self._headers(access), params=params)
        if response.status_code == 429:
            raise AppError("Slack rate limit reached", status_code=429, code="slack_rate_limited", user_message="Slack asked Synzept to slow down. Sync again after the rate limit resets.")
        if response.status_code >= 500:
            raise AppError("Slack unavailable", status_code=503, code="slack_unavailable", user_message="Slack is unavailable right now.")
        if response.status_code >= 400:
            raise AppError("Slack sync failed", status_code=400, code="sync_failed", user_message="Slack sync failed.")
        payload = response.json()
        if not payload.get("ok"):
            error = str(payload.get("error") or "sync_failed")
            if error in {"invalid_auth", "token_revoked", "account_inactive", "not_authed"}:
                raise AppError("Slack permission expired", status_code=409, code="permission_revoked", user_message="Slack authorization expired. Reconnect to continue.")
            if error in {"missing_scope", "not_allowed_token_type"}:
                raise AppError("Slack read permission denied", status_code=403, code="slack_permission_denied", user_message="Slack did not grant the required read-only permission. Reconnect and approve the listed permissions.")
            raise AppError(f"Slack API error: {error}", status_code=400, code="sync_failed", user_message="Slack sync failed.")
        return payload

    async def _access_token(self, account: ConnectedAppAccount) -> str:
        if account.encrypted_refresh_token:
            return await self.oauth.access_token(account, label="Slack", token_url=TOKEN_URL, client_id=self.settings.slack_client_id, client_secret=self.settings.slack_client_secret, success_field="ok")
        if account.encrypted_access_token:
            return self.oauth.decrypt(account.encrypted_access_token)
        raise AppError("Slack authorization expired", status_code=409, code="token_expired", user_message="Reconnect Slack to continue syncing.")

    async def _exchange_code(self, code: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(TOKEN_URL, data={"client_id": self.settings.slack_client_id, "client_secret": self.settings.slack_client_secret, "code": code, "redirect_uri": self._redirect_uri()})
        if response.status_code >= 400:
            raise AppError("Slack OAuth exchange failed", status_code=400, code="oauth_exchange_failed", user_message="Slack could not complete authorization.")
        payload = response.json()
        if not payload.get("ok"):
            raise AppError("Slack OAuth exchange failed", status_code=400, code="oauth_exchange_failed", user_message="Slack could not complete authorization.")
        return payload

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
            "permissions": ["Read workspace, user, joined channel, mention, thread, and recent conversation activity"] if account else [],
            "scopes": account.scopes if account else [],
            "privacy": {
                "why": "Slack helps Synzept understand collaboration patterns, explicit blockers, pending decisions, and team activity.",
                "reads": "Workspace, user, joined-channel, mention, thread, and recent conversation metadata. Recent text is processed transiently only to detect mentions and explicit blocker or decision language.",
                "usage": "Collaboration evidence becomes an observation and requires approval before changing understanding. Raw Slack message text is never stored.",
                "ignored": "Synzept cannot send or post messages, edit conversations, delete anything, or access channels the installed app cannot see.",
            },
        }

    def _encode_state(self, user_id: UUID) -> str:
        return jwt.encode({"sub": str(user_id), "provider": PROVIDER, "nonce": secrets.token_urlsafe(12), "exp": datetime.now(timezone.utc) + timedelta(minutes=15), "type": "slack_oauth_state"}, self.settings.jwt_secret_key, algorithm=self.settings.jwt_algorithm)

    def _decode_state(self, state: str) -> UUID:
        try:
            payload = jwt.decode(state, self.settings.jwt_secret_key, algorithms=[self.settings.jwt_algorithm])
            if payload.get("type") != "slack_oauth_state" or payload.get("provider") != PROVIDER:
                raise ValueError
            return UUID(str(payload["sub"]))
        except (JWTError, ValueError, KeyError) as exc:
            raise AppError("Invalid Slack OAuth state", status_code=400, code="invalid_oauth_state") from exc

    def _state_nonce(self, state: str) -> str:
        try:
            payload = jwt.decode(state, self.settings.jwt_secret_key, algorithms=[self.settings.jwt_algorithm])
            return str(payload["nonce"])
        except (JWTError, KeyError, TypeError) as exc:
            raise AppError("Invalid Slack OAuth state", status_code=400, code="invalid_oauth_state") from exc

    def _require_config(self) -> None:
        if not self.settings.slack_client_id or not self.settings.slack_client_secret:
            raise AppError("Slack is not configured", status_code=503, code="slack_not_configured", user_message="Slack is not configured for this Synzept environment yet.")

    def _redirect_uri(self) -> str:
        return self.settings.slack_redirect_uri or f"{self.settings.frontend_url.rstrip('/').replace('localhost:3000', 'localhost:8000')}/api/connected-apps/slack/callback"

    @staticmethod
    def _headers(access: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {access}", "Accept": "application/json"}

    @staticmethod
    def _slack_datetime(value: str) -> datetime | None:
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
