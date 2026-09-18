from __future__ import annotations

import base64
import hashlib
import logging
import re
import secrets
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError
from app.models.connected_app import CalendarEvent, ConnectedAppAccount, GoogleContact
from app.models.learning import LearningObservation
from app.models.user import User
from app.services.connected_apps.connected_app_action_service import ConnectedAppActionPreparationService

PROVIDER = "google_calendar"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    synced: int = 0
    updated: int = 0
    cancelled: int = 0
    observations: int = 0
    status: str = "connected"


class GoogleCalendarService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def status(self, user_id: UUID) -> dict:
        account = await self._account(user_id)
        if not account:
            return self._status_out(None)
        return self._status_out(account)

    async def authorization_url(self, user: User) -> dict:
        self._require_config()
        account = await self._account(user.id)
        if account:
            account.status = "connecting"
            account.last_error_code = None
            account.last_error_message = None
        else:
            account = ConnectedAppAccount(user_id=user.id, provider=PROVIDER, status="connecting", scopes=[CALENDAR_SCOPE])
            self.session.add(account)
        state = self._encode_state(user.id)
        account.app_metadata = {**(account.app_metadata or {}), "oauth_state_nonce": self._state_nonce(state)}
        await self.session.flush()
        params = {
            "client_id": self.settings.google_connected_apps_client_id,
            "redirect_uri": self._redirect_uri(),
            "response_type": "code",
            "scope": CALENDAR_SCOPE,
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
        }
        return {"authorizationUrl": f"{AUTH_URL}?{urlencode(params)}"}

    async def handle_callback(self, code: str | None, state: str | None, error: str | None, expected_user_id: UUID | None = None) -> str:
        self._require_config()
        frontend = self.settings.frontend_url.rstrip("/")
        if error:
            user_id = self._decode_state_user(state)
            if user_id is None:
                raise AppError("Invalid Google OAuth state", status_code=400, code="invalid_oauth_state")
            if expected_user_id is not None and user_id != expected_user_id:
                raise AppError("Invalid Google OAuth state", status_code=400, code="invalid_oauth_state")
            if user_id:
                await self._consume_state_nonce(user_id, self._state_nonce(state or ""))
                await self._mark_error(user_id, "oauth_cancelled", "Google Calendar connection was cancelled before permission was granted.")
            return f"{frontend}/connected?googleCalendar=cancelled"
        if not state:
            return f"{frontend}/connected?googleCalendar=error"

        user_id = self._decode_state(state)
        if expected_user_id is not None and user_id != expected_user_id:
            raise AppError("Invalid Google OAuth state", status_code=400, code="invalid_oauth_state")
        await self._consume_state_nonce(user_id, self._state_nonce(state))
        account = await self._ensure_account(user_id)
        if not code:
            await self._set_account_error(account, "oauth_missing_code", "Google Calendar did not return an authorization code.")
            return f"{frontend}/connected?googleCalendar=error"
        try:
            tokens = await self._exchange_code(code)
        except AppError as exc:
            logger.exception(
                "Google Calendar OAuth callback failed user_id=%s error_code=%s redirect_uri=%s client_id=%s scopes=%s",
                user_id,
                exc.code,
                self._redirect_uri(),
                self._masked_client_id(),
                [CALENDAR_SCOPE],
            )
            await self._set_account_error(account, "oauth_exchange_failed", exc.user_message or "Google did not complete the connection.")
            params = {"googleCalendar": "error"}
            if self._is_development():
                params["googleCalendarError"] = self._safe_development_error(exc)
            return f"{frontend}/connected?{urlencode(params)}"

        refresh_token = tokens.get("refresh_token")
        if not refresh_token and account.encrypted_refresh_token:
            refresh_token = self._decrypt(account.encrypted_refresh_token)
        if not refresh_token:
            await self._set_account_error(account, "missing_refresh_token", "Google did not return offline access. Reconnect and approve Calendar access again.")
            return f"{frontend}/connected?googleCalendar=reconnect"

        account.encrypted_refresh_token = self._encrypt(refresh_token)
        account.encrypted_access_token = self._encrypt(str(tokens.get("access_token") or ""))
        account.access_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(tokens.get("expires_in") or 3600) - 60)
        account.scopes = sorted(set(str(tokens.get("scope") or CALENDAR_SCOPE).split()))
        account.status = "connected"
        account.last_error_code = None
        account.last_error_message = None
        await self.session.flush()

        try:
            await self.sync(user_id)
        except Exception:
            account.status = "error"
            account.last_error_code = "sync_failed"
            account.last_error_message = "Calendar connected, but the first sync did not complete. Try manual sync."
        return f"{frontend}/connected?googleCalendar=connected"

    async def sync(self, user_id: UUID, *, full: bool = False) -> SyncResult:
        account = await self._required_account(user_id)
        if not account.encrypted_refresh_token:
            await self._set_account_error(account, "permission_revoked", "Google Calendar needs to be reconnected.")
            return SyncResult(status="permission_revoked")

        account.status = "syncing"
        await self.session.flush()
        try:
            access_token = await self._valid_access_token(account)
            result = await self._sync_events(account, access_token, full=full)
            result.observations = await self._create_observations(user_id)
            if result.observations:
                calendar_context = await self.calendar_context(user_id)
                upcoming_meetings = [*calendar_context.get("today", []), *calendar_context.get("tomorrow", [])][:4]
                await ConnectedAppActionPreparationService(self.session).prepare_for_provider(
                    user_id=user_id,
                    provider=PROVIDER,
                    observations_created=result.observations,
                    account_metadata={
                        "recent_event_count": result.synced,
                        "upcoming_meetings": upcoming_meetings,
                    },
                )
            account.status = "connected"
            account.last_synced_at = datetime.now(timezone.utc)
            account.last_error_code = None
            account.last_error_message = None
            await self.session.flush()
            return result
        except (AppError, httpx.TimeoutException, httpx.RequestError) as exc:
            code = exc.code if isinstance(exc, AppError) else "provider_unavailable"
            status = "permission_revoked" if code in {"permission_revoked", "token_expired"} else "error"
            message = exc.user_message if isinstance(exc, AppError) else "Google Calendar is unavailable right now. Try again later."
            await self._set_account_error(account, code, message, status=status)
            return SyncResult(status=status)

    async def disconnect(self, user_id: UUID) -> dict:
        account = await self._required_account(user_id)
        refresh = self._try_decrypt(account.encrypted_refresh_token)
        access = self._try_decrypt(account.encrypted_access_token)
        token = refresh or access
        if token:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(REVOKE_URL, params={"token": token})
            except httpx.RequestError:
                logger.warning("Google Calendar token revocation request failed; clearing local credentials")
        account.status = "not_connected"
        account.encrypted_refresh_token = None
        account.encrypted_access_token = None
        account.access_token_expires_at = None
        account.sync_token = None
        account.last_error_code = None
        account.last_error_message = None
        await self.session.flush()
        return self._status_out(account)

    async def calendar_context(self, user_id: UUID) -> dict:
        account = await self._account(user_id)
        if not account or account.status == "not_connected":
            return self._empty_calendar_context("Connect Google Calendar to see your schedule here.")
        if account.status in {"permission_revoked", "error"} or not self._try_decrypt(account.encrypted_refresh_token):
            return self._empty_calendar_context("Reconnect Google Calendar to refresh your schedule.")
        events = await self._events_between(user_id, self._day_start(date.today()), self._day_start(date.today() + timedelta(days=2)))
        contact_rows = list(
            (
                await self.session.execute(
                    select(GoogleContact).where(GoogleContact.user_id == user_id, GoogleContact.deleted.is_(False))
                )
            ).scalars()
        )
        contacts = {email.casefold(): row for row in contact_rows for email in row.emails if email}
        today = [item for item in events if item.start_at and item.start_at.date() == date.today() and item.status != "cancelled"]
        tomorrow = [item for item in events if item.start_at and item.start_at.date() == date.today() + timedelta(days=1) and item.status != "cancelled"]
        conflicts = self._conflicts(today)
        free_blocks = self._free_blocks(today)
        meeting_minutes = sum(self._duration_minutes(item) for item in today if item.busy)
        return {
            "today": [self._event_context(item, contacts) for item in today[:8]],
            "tomorrow": [self._event_context(item, contacts) for item in tomorrow[:6]],
            "meetingLoadMinutes": meeting_minutes,
            "freeBlocks": free_blocks[:4],
            "conflicts": conflicts[:4],
            "recommendation": self._calendar_recommendation(today, free_blocks, conflicts),
        }

    @staticmethod
    def _empty_calendar_context(recommendation: str) -> dict:
        return {
            "today": [],
            "tomorrow": [],
            "meetingLoadMinutes": 0,
            "freeBlocks": [],
            "conflicts": [],
            "recommendation": recommendation,
        }

    async def list_upcoming_events(
        self,
        *,
        user_id: UUID,
        start: datetime,
        end: datetime,
        query: str = "",
        max_results: int = 10,
    ) -> list[dict]:
        """Return bounded, user-owned event data for trusted agent tools."""
        account = await self._required_account(user_id)
        if account.status != "connected":
            raise NotFoundError("Google Calendar is not connected")
        readable_scopes = {CALENDAR_SCOPE, "https://www.googleapis.com/auth/calendar"}
        if account.scopes and not readable_scopes.intersection(account.scopes):
            raise AppError("Google Calendar read permission is missing", status_code=409, code="permission_missing", user_message="Reconnect Google Calendar with permission to read events.")
        events = await self._events_between(user_id, start, end)
        lowered = query.casefold().strip()
        if lowered:
            events = [event for event in events if lowered in f"{event.title} {event.description}".casefold()]
        return [self._agent_event_context(event) for event in events[: min(max_results, 20)] if event.status != "cancelled"]

    @classmethod
    def _agent_event_context(cls, event: CalendarEvent) -> dict:
        payload = cls._event_context(event)
        for key in ("startAt", "endAt", "start", "end"):
            value = payload.get(key)
            if isinstance(value, datetime):
                payload[key] = value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return payload

    async def weekly_context(self, user_id: UUID) -> dict:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=7)
        events = [item for item in await self._events_between(user_id, start, end) if item.status != "cancelled"]
        meeting_minutes = sum(self._duration_minutes(item) for item in events if item.busy)
        day_counts = Counter(item.start_at.date().isoformat() for item in events if item.start_at and item.busy)
        recurring = sum(1 for item in events if item.recurring)
        heavy_days = [day for day, count in day_counts.items() if count >= 5]
        return {
            "events": len(events),
            "meetingLoadMinutes": meeting_minutes,
            "recurringEvents": recurring,
            "heavyMeetingDays": heavy_days,
            "summary": self._weekly_summary(len(events), meeting_minutes, recurring, heavy_days),
        }

    async def sync_due_accounts(self, *, max_accounts: int = 25) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
        result = await self.session.execute(
            select(ConnectedAppAccount)
            .where(
                ConnectedAppAccount.provider == PROVIDER,
                ConnectedAppAccount.status.in_(["connected", "error"]),
                or_(ConnectedAppAccount.last_synced_at.is_(None), ConnectedAppAccount.last_synced_at < cutoff),
            )
            .order_by(ConnectedAppAccount.last_synced_at.asc().nullsfirst())
            .limit(max_accounts)
        )
        synced = 0
        for account in result.scalars():
            try:
                await self.sync(account.user_id)
                synced += 1
            except Exception:
                continue
        return synced

    async def _sync_events(self, account: ConnectedAppAccount, access_token: str, *, full: bool) -> SyncResult:
        params: dict[str, Any] = {
            "singleEvents": "true",
            "showDeleted": "true",
            "maxResults": "2500",
        }
        if account.sync_token and not full:
            params["syncToken"] = account.sync_token
        else:
            params["timeMin"] = self._rfc3339(datetime.now(timezone.utc) - timedelta(days=30))
            params["timeMax"] = self._rfc3339(datetime.now(timezone.utc) + timedelta(days=90))
            params["orderBy"] = "startTime"

        result = SyncResult()
        next_sync_token: str | None = None
        page_token: str | None = None
        async with httpx.AsyncClient(timeout=25) as client:
            while True:
                request_params = dict(params)
                if page_token:
                    request_params["pageToken"] = page_token
                response = await client.get(EVENTS_URL, params=request_params, headers={"Authorization": f"Bearer {access_token}"})
                if response.status_code == 410 and account.sync_token:
                    account.sync_token = None
                    return await self._sync_events(account, access_token, full=True)
                if response.status_code in {401, 403}:
                    raise AppError("Google Calendar permission was revoked", status_code=409, code="permission_revoked", user_message="Google Calendar permission was revoked. Reconnect Calendar to resume sync.")
                if response.status_code >= 500:
                    raise AppError("Google Calendar is unavailable", status_code=503, code="google_unavailable", user_message="Google Calendar is unavailable right now. Try syncing again later.")
                if response.status_code >= 400:
                    raise AppError("Google Calendar sync failed", status_code=400, code="sync_failed", user_message="Google Calendar sync failed. Try manual sync.")
                payload = response.json()
                for raw in payload.get("items", []):
                    event, created = await self._upsert_event(account, raw)
                    result.synced += 1
                    result.updated += 0 if created else 1
                    if event.status == "cancelled":
                        result.cancelled += 1
                page_token = payload.get("nextPageToken")
                next_sync_token = payload.get("nextSyncToken") or next_sync_token
                if not page_token:
                    break
        if next_sync_token:
            account.sync_token = next_sync_token
        return result

    async def _upsert_event(self, account: ConnectedAppAccount, raw: dict) -> tuple[CalendarEvent, bool]:
        provider_event_id = str(raw.get("id") or raw.get("iCalUID") or secrets.token_urlsafe(12))
        result = await self.session.execute(
            select(CalendarEvent).where(
                CalendarEvent.user_id == account.user_id,
                CalendarEvent.provider == PROVIDER,
                CalendarEvent.provider_event_id == provider_event_id,
            )
        )
        event = result.scalar_one_or_none()
        created = event is None
        if not event:
            event = CalendarEvent(user_id=account.user_id, connected_account_id=account.id, provider=PROVIDER, provider_event_id=provider_event_id)
            self.session.add(event)

        start_at, all_day = self._parse_event_time(raw.get("start") or {})
        end_at, _ = self._parse_event_time(raw.get("end") or {})
        event.calendar_id = "primary"
        event.i_cal_uid = raw.get("iCalUID")
        event.recurring_event_id = raw.get("recurringEventId")
        event.status = raw.get("status") or "confirmed"
        event.title = (raw.get("summary") or "Busy").strip()[:300]
        event.description = (raw.get("description") or "").strip()[:2000]
        event.location = (raw.get("location") or "").strip()[:300]
        event.start_at = start_at
        event.end_at = end_at
        event.all_day = all_day
        event.recurring = bool(raw.get("recurringEventId") or raw.get("recurrence"))
        event.busy = raw.get("transparency") != "transparent" and event.status != "cancelled"
        event.html_link = raw.get("htmlLink")
        event.event_metadata = {
            "etag": raw.get("etag"),
            "updated": raw.get("updated"),
            "eventType": raw.get("eventType"),
            "hangoutLink": bool(raw.get("hangoutLink")),
            "attendees": [
                {"name": str(item.get("displayName") or ""), "email": str(item.get("email") or "")}
                for item in (raw.get("attendees") or [])[:10]
                if isinstance(item, dict) and (item.get("displayName") or item.get("email"))
            ],
            "organizer": {
                "name": str((raw.get("organizer") or {}).get("displayName") or ""),
                "email": str((raw.get("organizer") or {}).get("email") or ""),
            } if isinstance(raw.get("organizer"), dict) else {},
        }
        return event, created

    async def _valid_access_token(self, account: ConnectedAppAccount) -> str:
        now = datetime.now(timezone.utc)
        if account.encrypted_access_token and account.access_token_expires_at:
            expires = account.access_token_expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires > now + timedelta(minutes=2):
                return self._decrypt(account.encrypted_access_token)
        refresh = self._decrypt(account.encrypted_refresh_token or "")
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                TOKEN_URL,
                data={
                    "client_id": self.settings.google_connected_apps_client_id,
                    "client_secret": self.settings.google_connected_apps_client_secret,
                    "refresh_token": refresh,
                    "grant_type": "refresh_token",
                },
            )
        if response.status_code in {400, 401}:
            raise AppError("Google Calendar permission was revoked", status_code=409, code="permission_revoked", user_message="Google Calendar permission was revoked. Reconnect Calendar to resume sync.")
        if response.status_code >= 500:
            raise AppError("Google token refresh failed", status_code=503, code="google_unavailable", user_message="Google is unavailable right now. Try again later.")
        if response.status_code >= 400:
            raise AppError("Google token refresh failed", status_code=400, code="token_expired", user_message="Google Calendar authorization expired. Reconnect Calendar.")
        tokens = response.json()
        access = str(tokens["access_token"])
        account.encrypted_access_token = self._encrypt(access)
        account.access_token_expires_at = now + timedelta(seconds=int(tokens.get("expires_in") or 3600) - 60)
        return access

    async def _exchange_code(self, code: str) -> dict:
        redirect_uri = self._redirect_uri()
        token_payload = {
            "code": code,
            "client_id": self.settings.google_connected_apps_client_id,
            "client_secret": self.settings.google_connected_apps_client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        log_context = {
            "token_endpoint": TOKEN_URL,
            "redirect_uri": redirect_uri,
            "client_id": self._masked_client_id(),
            "scopes": [CALENDAR_SCOPE],
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(TOKEN_URL, data=token_payload)
        except Exception as exc:
            logger.exception(
                "Google Calendar OAuth token exchange request failed token_endpoint=%s redirect_uri=%s client_id=%s scopes=%s",
                log_context["token_endpoint"],
                log_context["redirect_uri"],
                log_context["client_id"],
                log_context["scopes"],
            )
            raise AppError(
                f"Google OAuth exchange request failed: {type(exc).__name__}: {exc}",
                status_code=400,
                code="oauth_exchange_failed",
                user_message="Google did not complete the Calendar connection. Try again.",
            ) from exc
        if response.status_code >= 400:
            response_body = self._safe_response_body(response, extra_secrets=(code,))
            logger.error(
                "Google Calendar OAuth token exchange failed token_endpoint=%s redirect_uri=%s client_id=%s scopes=%s status=%s response_body=%s",
                log_context["token_endpoint"],
                log_context["redirect_uri"],
                log_context["client_id"],
                log_context["scopes"],
                response.status_code,
                response_body,
            )
            raise AppError(
                f"Google OAuth exchange failed: status={response.status_code} response_body={response_body}",
                status_code=400,
                code="oauth_exchange_failed",
                user_message="Google did not complete the Calendar connection. Try again.",
            )
        return response.json()

    async def _create_observations(self, user_id: UUID) -> int:
        start = datetime.now(timezone.utc) - timedelta(days=35)
        events = [item for item in await self._events_between(user_id, start, datetime.now(timezone.utc) + timedelta(days=35)) if item.status != "cancelled" and item.start_at]
        observations: list[str] = []
        by_title: dict[str, list[CalendarEvent]] = defaultdict(list)
        for event in events:
            title = self._normalize_title(event.title)
            if title and event.recurring:
                by_title[title].append(event)
        for title, rows in by_title.items():
            if len({row.start_at.date() for row in rows if row.start_at}) >= 3:
                observations.append(f"Calendar pattern: recurring {title} appears {len(rows)} times.")
        weekday_busy = Counter()
        for event in events:
            if event.busy and event.start_at and event.start_at.weekday() < 5:
                weekday_busy[event.start_at.weekday()] += self._duration_minutes(event)
        if sum(1 for minutes in weekday_busy.values() if minutes >= 300) >= 4:
            observations.append("Calendar pattern: weekdays appear heavily scheduled during work hours.")
        if sum(1 for event in events if self._contains(event.title, "flight", "airport", "travel", "train")) >= 2:
            observations.append("Calendar pattern: frequent travel appears in scheduled events.")

        existing = {
            item.content
            for item in (
                await self.session.execute(
                    select(LearningObservation).where(LearningObservation.user_id == user_id, LearningObservation.source == PROVIDER)
                )
            ).scalars()
        }
        created = 0
        for content in observations:
            if content in existing:
                continue
            self.session.add(LearningObservation(user_id=user_id, source=PROVIDER, content=content, status="observed"))
            created += 1
        await self.session.flush()
        return created

    async def _events_between(self, user_id: UUID, start: datetime, end: datetime) -> list[CalendarEvent]:
        result = await self.session.execute(
            select(CalendarEvent)
            .where(CalendarEvent.user_id == user_id, CalendarEvent.start_at.is_not(None), CalendarEvent.start_at >= start, CalendarEvent.start_at < end)
            .order_by(CalendarEvent.start_at.asc())
        )
        return list(result.scalars())

    async def _account(self, user_id: UUID) -> ConnectedAppAccount | None:
        result = await self.session.execute(select(ConnectedAppAccount).where(ConnectedAppAccount.user_id == user_id, ConnectedAppAccount.provider == PROVIDER))
        return result.scalar_one_or_none()

    async def _ensure_account(self, user_id: UUID) -> ConnectedAppAccount:
        account = await self._account(user_id)
        if account:
            return account
        account = ConnectedAppAccount(user_id=user_id, provider=PROVIDER, status="connecting", scopes=[CALENDAR_SCOPE])
        self.session.add(account)
        await self.session.flush()
        return account

    async def _required_account(self, user_id: UUID) -> ConnectedAppAccount:
        account = await self._account(user_id)
        if not account or account.status == "not_connected":
            raise NotFoundError("Google Calendar is not connected")
        return account

    async def _mark_error(self, user_id: UUID, code: str, message: str) -> None:
        account = await self._ensure_account(user_id)
        await self._set_account_error(account, code, message)

    async def _set_account_error(self, account: ConnectedAppAccount, code: str, message: str, *, status: str = "error") -> None:
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
            "permissions": ["Read calendar events"] if account and account.scopes else [],
            "scopes": account.scopes if account else [],
            "privacy": {
                "why": "Calendar helps Synzept understand commitments, available time, meeting load, and scheduling conflicts.",
                "reads": "Event title, start/end time, status, recurrence, location, and availability from your primary calendar.",
                "usage": "Calendar data informs Daily Brief, Chat continuity, Weekly Review, and learning observations that require approval before becoming understanding.",
            },
        }

    def _encode_state(self, user_id: UUID) -> str:
        payload = {
            "sub": str(user_id),
            "nonce": secrets.token_urlsafe(12),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "type": "google_calendar_oauth_state",
        }
        return jwt.encode(payload, self.settings.jwt_secret_key, algorithm=self.settings.jwt_algorithm)

    def _decode_state(self, state: str) -> UUID:
        try:
            payload = jwt.decode(state, self.settings.jwt_secret_key, algorithms=[self.settings.jwt_algorithm])
        except JWTError as exc:
            raise AppError("Invalid Google OAuth state", status_code=400, code="invalid_oauth_state") from exc
        if payload.get("type") != "google_calendar_oauth_state":
            raise AppError("Invalid Google OAuth state", status_code=400, code="invalid_oauth_state")
        return UUID(payload["sub"])

    def _decode_state_user(self, state: str | None) -> UUID | None:
        if not state:
            return None
        try:
            return self._decode_state(state)
        except AppError:
            return None

    def _state_nonce(self, state: str) -> str:
        try:
            payload = jwt.decode(state, self.settings.jwt_secret_key, algorithms=[self.settings.jwt_algorithm])
            return str(payload["nonce"])
        except (JWTError, KeyError, TypeError) as exc:
            raise AppError("Invalid Google OAuth state", status_code=400, code="invalid_oauth_state") from exc

    async def _consume_state_nonce(self, user_id: UUID, nonce: str) -> None:
        account = await self._account(user_id)
        if not account or (account.app_metadata or {}).get("oauth_state_nonce") != nonce:
            raise AppError("Google OAuth state has already been used", status_code=400, code="invalid_oauth_state")
        metadata = dict(account.app_metadata or {})
        metadata.pop("oauth_state_nonce", None)
        account.app_metadata = metadata
        await self.session.flush()

    def _encrypt(self, value: str) -> str:
        return self._fernet().encrypt(value.encode()).decode()

    def _decrypt(self, value: str) -> str:
        try:
            return self._fernet().decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise AppError("Stored Google token could not be decrypted", status_code=409, code="token_expired", user_message="Reconnect Google Calendar to refresh authorization.") from exc

    def _try_decrypt(self, value: str | None) -> str | None:
        if not value:
            return None
        try:
            return self._decrypt(value)
        except AppError:
            return None

    def _fernet(self) -> Fernet:
        secret = self.settings.connected_app_token_secret
        if not secret:
            raise AppError(
                "Connected-app encryption is not configured",
                status_code=503,
                code="google_calendar_not_configured",
                user_message="Google Connected Apps are not configured for this environment yet.",
            )
        digest = hashlib.sha256(secret.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(digest))

    def _require_config(self) -> None:
        if (
            not self.settings.google_connected_apps_client_id
            or not self.settings.google_connected_apps_client_secret
            or not self.settings.google_connected_apps_redirect_uri
            or not self.settings.connected_app_token_secret
        ):
            raise AppError("Google Calendar is not configured", status_code=503, code="google_calendar_not_configured", user_message="Google Calendar is not configured for this Synzept environment yet.")

    def _redirect_uri(self) -> str:
        if self.settings.google_connected_apps_redirect_uri:
            return self.settings.google_connected_apps_redirect_uri
        if (self.settings.environment or "").lower() not in {"development", "dev", "local", "test", "testing"}:
            raise AppError("Google Connected Apps redirect URI is not configured", status_code=503, code="google_calendar_not_configured", user_message="Google Connected Apps are not configured for this environment yet.")
        return f"{self.settings.frontend_url.rstrip('/').replace('localhost:3000', 'localhost:8000')}/api/connected-apps/google-calendar/callback"

    def _masked_client_id(self) -> str:
        value = self.settings.google_connected_apps_client_id or ""
        if not value:
            return "missing"
        if len(value) <= 10:
            return f"{value[:2]}...{value[-2:]}"
        return f"{value[:6]}...{value[-4:]}"

    def _is_development(self) -> bool:
        return (self.settings.environment or "").lower() in {"development", "dev", "local", "test", "testing"}

    def _safe_response_body(self, response: httpx.Response, *, extra_secrets: tuple[str, ...] = ()) -> str:
        body = response.text.strip()
        if not body:
            return "<empty>"
        return self._sanitize_for_logs(body[:4000], extra_secrets=extra_secrets)

    def _safe_development_error(self, exc: AppError) -> str:
        return self._sanitize_for_logs(str(exc.message)[:1000])

    def _sanitize_for_logs(self, value: str, *, extra_secrets: tuple[str, ...] = ()) -> str:
        sanitized = value
        secret_values = (
            self.settings.google_connected_apps_client_secret,
            self.settings.connected_app_token_secret,
            self.settings.jwt_secret_key,
            *extra_secrets,
        )
        for secret in secret_values:
            if secret:
                sanitized = sanitized.replace(secret, "[redacted]")
        if self.settings.google_connected_apps_client_id:
            sanitized = sanitized.replace(self.settings.google_connected_apps_client_id, self._masked_client_id())
        return sanitized

    @staticmethod
    def _parse_event_time(value: dict) -> tuple[datetime | None, bool]:
        if "dateTime" in value:
            parsed = datetime.fromisoformat(str(value["dateTime"]).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc), False
        if "date" in value:
            parsed_date = date.fromisoformat(str(value["date"]))
            return datetime.combine(parsed_date, time.min, tzinfo=timezone.utc), True
        return None, False

    @staticmethod
    def _rfc3339(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _day_start(value: date) -> datetime:
        return datetime.combine(value, time.min, tzinfo=timezone.utc)

    @staticmethod
    def _event_context(event: CalendarEvent, contacts: dict[str, GoogleContact] | None = None) -> dict:
        contacts = contacts or {}
        matched = []
        title = getattr(event, "title", "") or ""
        event_title = title
        for email in re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", event_title, flags=re.IGNORECASE):
            contact = contacts.get(email.casefold())
            if not contact or not contact.display_name:
                continue
            title = re.sub(re.escape(email), contact.display_name, title, flags=re.IGNORECASE)
            matched.append(
                {
                    "name": contact.display_name,
                    "company": contact.company or None,
                    "jobTitle": contact.job_title or None,
                    "relationship": list((contact.relationship_metadata or {}).get("relations") or [])[:2],
                }
            )
        metadata = getattr(event, "event_metadata", None) or {}
        if not isinstance(metadata, dict):
            metadata = {}
        attendees = metadata.get("attendees") if isinstance(metadata.get("attendees"), list) else []
        organizer = metadata.get("organizer") if isinstance(metadata.get("organizer"), dict) else {}
        return {
            "event_id": getattr(event, "provider_event_id", None),
            "title": title,
            "startAt": getattr(event, "start_at", None),
            "endAt": getattr(event, "end_at", None),
            "start": getattr(event, "start_at", None),
            "end": getattr(event, "end_at", None),
            "description": getattr(event, "description", "") or "",
            "location": getattr(event, "location", "") or "",
            "organizer": {"name": str(organizer.get("name") or ""), "email": str(organizer.get("email") or "")},
            "attendees": attendees[:10],
            "status": getattr(event, "status", "confirmed"),
            "recurring": bool(getattr(event, "recurring", False)),
            "busy": bool(getattr(event, "busy", True)),
            "people": matched,
        }

    @staticmethod
    def _duration_minutes(event: CalendarEvent) -> int:
        if not event.start_at or not event.end_at:
            return 0
        return max(0, round((event.end_at - event.start_at).total_seconds() / 60))

    @classmethod
    def _conflicts(cls, events: list[CalendarEvent]) -> list[str]:
        conflicts: list[str] = []
        busy = [event for event in events if event.busy and event.start_at and event.end_at]
        for index, current in enumerate(busy):
            for other in busy[index + 1 :]:
                current_start = cls._as_utc(current.start_at) if current.start_at else None
                current_end = cls._as_utc(current.end_at) if current.end_at else None
                other_start = cls._as_utc(other.start_at) if other.start_at else None
                other_end = cls._as_utc(other.end_at) if other.end_at else None
                if current_start and current_end and other_start and other_start < current_end and other_end and other_end > current_start:
                    conflicts.append(f"{current.title} overlaps with {other.title}.")
        return conflicts

    @classmethod
    def _free_blocks(cls, events: list[CalendarEvent]) -> list[dict]:
        work_start = datetime.combine(date.today(), time(9), tzinfo=timezone.utc)
        work_end = datetime.combine(date.today(), time(18), tzinfo=timezone.utc)
        cursor = work_start
        blocks: list[dict] = []
        busy = sorted([event for event in events if event.busy and event.start_at and event.end_at], key=lambda item: item.start_at or work_start)
        for event in busy:
            event_start = cls._as_utc(event.start_at) if event.start_at else None
            event_end = cls._as_utc(event.end_at) if event.end_at else None
            if event_start and event_start > cursor:
                minutes = round((event_start - cursor).total_seconds() / 60)
                if minutes >= 45:
                    blocks.append({"startAt": cursor, "endAt": event_start, "minutes": minutes})
            if event_end and event_end > cursor:
                cursor = event_end
        if cursor < work_end:
            minutes = round((work_end - cursor).total_seconds() / 60)
            if minutes >= 45:
                blocks.append({"startAt": cursor, "endAt": work_end, "minutes": minutes})
        return blocks

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _calendar_recommendation(events: list[CalendarEvent], free_blocks: list[dict], conflicts: list[str]) -> str:
        if conflicts:
            return "Review scheduling conflicts before committing to new work."
        longest = max((block["minutes"] for block in free_blocks), default=0)
        if longest >= 120:
            return "You have a two-hour focus block today. Use it for the most important unfinished work."
        if len(events) >= 5:
            return "Today is meeting-heavy. Keep the next action small and avoid over-planning."
        if events:
            return "Prepare for today's meetings, then protect one focused work block."
        return "No calendar commitments are visible today. This is a good day to choose one deep-work priority."

    @staticmethod
    def _weekly_summary(events: int, minutes: int, recurring: int, heavy_days: list[str]) -> str:
        hours = round(minutes / 60, 1)
        if heavy_days:
            return f"Calendar shows {hours} hours in events, with heavy meeting load on {len(heavy_days)} day(s)."
        if recurring >= 3:
            return f"Calendar shows {hours} scheduled hours and recurring commitments shaped the week."
        return f"Calendar shows {events} event(s) and {hours} scheduled hours this week."

    @staticmethod
    def _normalize_title(value: str) -> str:
        title = " ".join(value.lower().split())
        for prefix in ("weekly ", "daily ", "monthly "):
            title = title.removeprefix(prefix)
        return title[:80]

    @staticmethod
    def _contains(value: str, *needles: str) -> bool:
        text = value.casefold()
        return any(needle in text for needle in needles)
