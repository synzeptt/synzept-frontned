from __future__ import annotations

import logging
import re
import secrets
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from jose import JWTError, jwt
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.connected_app import (
    CalendarEvent,
    ConnectedAppAccount,
    MicrosoftContact,
    MicrosoftDriveItem,
    MicrosoftMailMessage,
    MicrosoftTeam,
    MicrosoftTeamChannel,
    MicrosoftTeamMembership,
    MicrosoftTeamsActivity,
    MicrosoftTask,
    MicrosoftTaskList,
)
from app.models.learning import LearningObservation
from app.models.user import User
from app.services.connected_apps.connected_app_action_service import ConnectedAppActionPreparationService
from app.services.connected_apps.oauth_lifecycle import ConnectedAppOAuthLifecycle

GRAPH_URL = "https://graph.microsoft.com/v1.0"
AUTHORIZE_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
LOGOUT_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/logout"
BASE_SCOPES = ("openid", "profile", "offline_access", "User.Read")
TEAMS_SIGNAL_BLOCKER = re.compile(r"\b(blocked|blocker|blocking|waiting on|waiting for|stuck on)\b", re.IGNORECASE)
TEAMS_SIGNAL_DECISION = re.compile(r"\b(decision pending|needs? a decision|awaiting (?:a )?decision|yet to decide|need to decide)\b", re.IGNORECASE)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MicrosoftProviderSpec:
    provider: str
    label: str
    permission_scope: str
    permission: str
    why: str
    reads: str
    usage: str
    ignored: str
    additional_scopes: tuple[str, ...] = ()

    @property
    def scopes(self) -> list[str]:
        return [*BASE_SCOPES, self.permission_scope, *self.additional_scopes]


MICROSOFT_PROVIDERS: dict[str, MicrosoftProviderSpec] = {
    "microsoft_outlook_mail": MicrosoftProviderSpec(
        "microsoft_outlook_mail", "Outlook Mail", "Mail.ReadBasic", "Read basic mail metadata",
        "Outlook metadata helps Synzept notice communication load, active conversations, and follow-ups.",
        "Message IDs, conversation IDs, sender, timestamps, read state, folder IDs, and categories.",
        "Mail evidence becomes an observation and must be approved before changing understanding.",
        "Synzept does not read bodies, previews, attachments, drafts, or send messages.",
    ),
    "microsoft_outlook_calendar": MicrosoftProviderSpec(
        "microsoft_outlook_calendar", "Outlook Calendar", "Calendars.Read", "Read calendars",
        "Outlook Calendar helps Synzept understand meetings, commitments, conflicts, and focus windows.",
        "Meeting titles, attendees, times, status, recurrence, location, and availability.",
        "Calendar evidence improves Today and Weekly Review through approval-gated observations.",
        "Synzept never creates, edits, deletes, accepts, or declines calendar events.",
    ),
    "microsoft_onedrive": MicrosoftProviderSpec(
        "microsoft_onedrive", "OneDrive", "Files.Read", "Read your files",
        "OneDrive metadata helps Synzept recognize active documents and project freshness.",
        "File names, types, modified timestamps, and lightweight sharing metadata.",
        "File activity becomes observation evidence before it can affect understanding.",
        "Synzept does not download file contents, edit files, delete files, or change sharing.",
    ),
    "microsoft_todo": MicrosoftProviderSpec(
        "microsoft_todo", "Microsoft To Do", "Tasks.Read", "Read tasks and task lists",
        "Microsoft To Do helps Synzept recognize open loops, overdue work, priorities, and completion patterns.",
        "Task names, lists, status, due/completed timestamps, importance, recurrence, and update timestamps.",
        "Task evidence improves prioritization through the existing observation approval pipeline.",
        "Synzept does not read task bodies or create, edit, delete, reorder, or complete tasks.",
    ),
    "microsoft_people": MicrosoftProviderSpec(
        "microsoft_people", "Microsoft People", "Contacts.Read", "Read contacts",
        "People helps Synzept resolve names and understand explicit professional relationship context.",
        "Names, email addresses, organizations, job titles, relationship metadata, and update timestamps.",
        "Relationship evidence remains an observation until you approve it.",
        "Synzept does not read photos, message contacts, edit contacts, delete contacts, or share contacts.",
    ),
    "microsoft_teams": MicrosoftProviderSpec(
        "microsoft_teams", "Microsoft Teams", "Team.ReadBasic.All", "Read Teams collaboration metadata",
        "Teams helps Synzept understand collaboration activity, meetings, blockers, and decisions that may need attention.",
        "Joined teams, channels, memberships, mentions, meeting metadata, thread activity, and recent collaboration timestamps.",
        "Teams evidence becomes an observation and must be approved before changing understanding.",
        "Synzept does not store message bodies, send or edit messages, create channels, join meetings, schedule meetings, or modify conversations.",
        ("Channel.ReadBasic.All", "TeamMember.Read.All", "ChannelMessage.Read.All", "Calendars.Read"),
    ),
}


@dataclass
class MicrosoftSyncResult:
    synced: int = 0
    updated: int = 0
    cancelled: int = 0
    observations: int = 0
    status: str = "connected"


class Microsoft365Service:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self.oauth = ConnectedAppOAuthLifecycle(session)

    async def statuses(self, user_id: UUID) -> list[dict]:
        return [await self.status(provider, user_id) for provider in MICROSOFT_PROVIDERS]

    async def status(self, provider: str, user_id: UUID) -> dict:
        spec = self._spec(provider)
        return self._status_out(spec, await self.oauth.account(user_id, provider))

    async def authorization_url(self, provider: str, user: User) -> dict:
        spec = self._spec(provider)
        self._require_config(spec)
        account = await self.oauth.ensure_account(user.id, provider, spec.scopes)
        account.status = "connecting"
        account.last_error_code = None
        account.last_error_message = None
        state = self._encode_state(user.id, provider)
        await self.oauth.store_state_nonce(account, self._state_nonce(state))
        params = {
            "client_id": self.settings.microsoft_client_id,
            "response_type": "code",
            "redirect_uri": self._redirect_uri(),
            "response_mode": "query",
            "scope": " ".join(spec.scopes),
            "state": state,
            "prompt": "select_account",
        }
        return {"authorizationUrl": f"{self._authorize_url()}?{urlencode(params)}"}

    async def handle_callback(self, code: str | None, state: str | None, error: str | None, expected_user_id: UUID | None = None) -> str:
        frontend = self.settings.frontend_url.rstrip("/")
        user_id, provider = self._decode_state(state or "")
        if expected_user_id is not None and user_id != expected_user_id:
            raise AppError("Invalid Microsoft OAuth state", status_code=400, code="invalid_oauth_state")
        spec = self._spec(provider)
        account = await self.oauth.ensure_account(user_id, provider, spec.scopes)
        await self.oauth.consume_state_nonce(account, self._state_nonce(state or ""), "Microsoft")
        if error:
            await self._set_error(account, "oauth_cancelled", f"{spec.label} connection was cancelled.")
            return f"{frontend}/connected?microsoft365=cancelled&microsoftService={provider}"
        if not code:
            await self._set_error(account, "oauth_missing_code", f"{spec.label} did not return an authorization code.")
            return f"{frontend}/connected?microsoft365=error&microsoftService={provider}"
        try:
            tokens = await self._exchange_code(code, spec)
            refresh = tokens.get("refresh_token") or self.oauth.try_decrypt(account.encrypted_refresh_token)
            if not refresh:
                raise AppError("Microsoft did not return offline access", status_code=400, code="missing_refresh_token")
            granted = str(tokens.get("scope") or "").split()
            missing = [scope for scope in spec.scopes if scope not in granted and scope not in BASE_SCOPES]
            if missing:
                raise AppError(f"Missing Microsoft permission {', '.join(missing)}", status_code=400, code="oauth_missing_scope")
            account.encrypted_refresh_token = self.oauth.encrypt(str(refresh))
            account.encrypted_access_token = self.oauth.encrypt(str(tokens.get("access_token") or ""))
            account.access_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(tokens.get("expires_in") or 3600) - 60)
            account.scopes = sorted(set(granted))
            account.status = "connected"
            account.last_error_code = None
            account.last_error_message = None
            await self._load_profile(account, str(tokens.get("access_token") or ""))
            await self.session.flush()
            await self.sync(provider, user_id)
            return f"{frontend}/connected?microsoft365=connected&microsoftService={provider}"
        except AppError as exc:
            await self._set_error(account, exc.code or "oauth_exchange_failed", exc.user_message or f"{spec.label} could not connect.")
            return f"{frontend}/connected?microsoft365=error&microsoftService={provider}"

    async def sync(self, provider: str, user_id: UUID) -> MicrosoftSyncResult:
        spec = self._spec(provider)
        account = await self.oauth.required_account(user_id, provider)
        if not account.encrypted_refresh_token:
            await self._set_error(account, "permission_revoked", f"{spec.label} needs to be reconnected.", "permission_revoked")
            return MicrosoftSyncResult(status="permission_revoked")
        account.status = "syncing"
        await self.session.flush()
        try:
            access = await self.oauth.access_token(
                account,
                label=spec.label,
                token_url=self._token_url(),
                client_id=self.settings.microsoft_client_id,
                client_secret=self.settings.microsoft_client_secret,
                extra_data={"scope": " ".join(spec.scopes)},
            )
            if provider == "microsoft_outlook_mail":
                result = await self._sync_mail(account, access)
            elif provider == "microsoft_outlook_calendar":
                result = await self._sync_calendar(account, access)
            elif provider == "microsoft_onedrive":
                result = await self._sync_drive(account, access)
            elif provider == "microsoft_todo":
                result = await self._sync_todo(account, access)
            elif provider == "microsoft_teams":
                result = await self._sync_teams(account, access)
            else:
                result = await self._sync_people(account, access)
            result.observations = await self._create_observations(account)
            if result.observations:
                upcoming_meetings = None
                if account.provider == "microsoft_outlook_calendar":
                    calendar_context = await self.calendar_context(account.user_id)
                    upcoming_meetings = [*calendar_context.get("today", []), *calendar_context.get("tomorrow", [])][:4]
                await ConnectedAppActionPreparationService(self.session).prepare_for_provider(
                    user_id=account.user_id,
                    provider=account.provider,
                    observations_created=result.observations,
                    account_metadata={
                        **(account.app_metadata or {}),
                        **({"upcoming_meetings": upcoming_meetings} if upcoming_meetings else {}),
                    },
                )
            account.status = "connected"
            account.last_synced_at = datetime.now(timezone.utc)
            account.last_error_code = None
            account.last_error_message = None
            await self.session.flush()
            return result
        except AppError as exc:
            status = "permission_revoked" if exc.code in {"permission_revoked", "token_expired"} else "error"
            await self._set_error(account, exc.code or "sync_failed", exc.user_message or f"{spec.label} sync failed.", status)
            return MicrosoftSyncResult(status=status)

    async def disconnect(self, provider: str, user_id: UUID) -> dict:
        spec = self._spec(provider)
        account = await self.oauth.required_account(user_id, provider)
        self.oauth.clear_tokens(account)
        await self.session.flush()
        return self._status_out(spec, account)

    async def sync_due_accounts(self, *, max_accounts: int = 25) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
        accounts = list(
            (
                await self.session.execute(
                    select(ConnectedAppAccount)
                    .where(
                        ConnectedAppAccount.provider.in_(tuple(MICROSOFT_PROVIDERS)),
                        ConnectedAppAccount.status.in_(("connected", "error")),
                        or_(ConnectedAppAccount.last_synced_at.is_(None), ConnectedAppAccount.last_synced_at < cutoff),
                    )
                    .order_by(ConnectedAppAccount.last_synced_at.asc().nullsfirst())
                    .limit(max_accounts)
                )
            ).scalars()
        )
        synced = 0
        for account in accounts:
            try:
                result = await self.sync(account.provider, account.user_id)
                synced += int(result.status == "connected")
            except Exception:
                logger.exception("Scheduled Microsoft 365 sync failed provider=%s user_id=%s", account.provider, account.user_id)
        return synced

    async def calendar_context(self, user_id: UUID) -> dict:
        await self.oauth.required_account(user_id, "microsoft_outlook_calendar")
        start = self._day_start(date.today())
        end = self._day_start(date.today() + timedelta(days=2))
        events = list((await self.session.execute(select(CalendarEvent).where(CalendarEvent.user_id == user_id, CalendarEvent.provider == "microsoft_outlook_calendar", CalendarEvent.start_at >= start, CalendarEvent.start_at < end))).scalars())
        today = [event for event in events if event.start_at and event.start_at.date() == date.today() and event.status != "cancelled"]
        tomorrow = [event for event in events if event.start_at and event.start_at.date() == date.today() + timedelta(days=1) and event.status != "cancelled"]
        conflicts = self._conflicts(today)
        free_blocks = self._free_blocks(today)
        return {
            "today": [self._calendar_item(event) for event in today[:8]],
            "tomorrow": [self._calendar_item(event) for event in tomorrow[:6]],
            "meetingLoadMinutes": sum(self._duration(event) for event in today if event.busy),
            "freeBlocks": free_blocks[:4],
            "conflicts": conflicts[:4],
            "recommendation": "Review scheduling conflicts before adding work." if conflicts else "Protect the clearest focus window around your Outlook commitments.",
        }

    async def weekly_context(self, user_id: UUID) -> dict:
        await self.oauth.required_account(user_id, "microsoft_outlook_calendar")
        now = datetime.now(timezone.utc)
        events = list((await self.session.execute(select(CalendarEvent).where(CalendarEvent.user_id == user_id, CalendarEvent.provider == "microsoft_outlook_calendar", CalendarEvent.start_at >= now - timedelta(days=7), CalendarEvent.start_at <= now))).scalars())
        minutes = sum(self._duration(event) for event in events if event.busy and event.status != "cancelled")
        recurring = sum(1 for event in events if event.recurring)
        return {"events": len(events), "meetingLoadMinutes": minutes, "recurringEvents": recurring, "heavyMeetingDays": [], "summary": f"Outlook shows {len(events)} event(s) and {round(minutes / 60, 1)} scheduled hours this week."}

    async def _sync_mail(self, account: ConnectedAppAccount, access: str) -> MicrosoftSyncResult:
        initial = f"{GRAPH_URL}/me/messages/delta?$select=id,conversationId,sender,receivedDateTime,isRead,parentFolderId,categories,lastModifiedDateTime"
        rows, delta = await self._delta_incremental(account.sync_token, initial, access)
        existing = {row.provider_message_id: row for row in (await self.session.execute(select(MicrosoftMailMessage).where(MicrosoftMailMessage.user_id == account.user_id))).scalars()}
        result = MicrosoftSyncResult()
        for raw in rows:
            item_id = str(raw.get("id") or "")
            if not item_id:
                continue
            item = existing.get(item_id)
            created = item is None
            if item is None:
                item = MicrosoftMailMessage(user_id=account.user_id, connected_account_id=account.id, provider_message_id=item_id)
                self.session.add(item)
                existing[item_id] = item
            removed = bool(raw.get("@removed"))
            sender = ((raw.get("sender") or {}).get("emailAddress") or {})
            item.conversation_id = str(raw.get("conversationId") or item.conversation_id or "")
            item.sender_name = str(sender.get("name") or item.sender_name or "")[:300]
            item.sender_email = str(sender.get("address") or item.sender_email or "").lower()[:320]
            item.received_at = self._datetime(raw.get("receivedDateTime")) or item.received_at
            item.is_read = bool(raw.get("isRead", item.is_read))
            item.folder_id = str(raw.get("parentFolderId") or item.folder_id or "")[:512]
            item.categories = [str(value)[:120] for value in raw.get("categories") or item.categories]
            item.deleted = removed
            result.cancelled += int(removed)
            result.synced += int(created and not removed)
            result.updated += int(not created and not removed)
        account.sync_token = delta or account.sync_token
        active = [item for item in existing.values() if not item.deleted]
        unread = [item for item in active if not item.is_read]
        user_email = str((account.app_metadata or {}).get("account_email") or "").casefold()
        latest_by_conversation: dict[str, MicrosoftMailMessage] = {}
        for item in active:
            current = latest_by_conversation.get(item.conversation_id)
            if item.conversation_id and (not current or self._aware(item.received_at or datetime.min) > self._aware(current.received_at or datetime.min)):
                latest_by_conversation[item.conversation_id] = item
        waiting = sum(1 for item in latest_by_conversation.values() if user_email and item.sender_email.casefold() == user_email and item.received_at and self._aware(item.received_at) < datetime.now(timezone.utc) - timedelta(days=2))
        account.app_metadata = {**(account.app_metadata or {}), "messages_count": len(active), "unread_messages_count": len(unread), "active_conversations_count": len(latest_by_conversation), "waiting_for_reply_count": waiting}
        return result

    async def _sync_calendar(self, account: ConnectedAppAccount, access: str) -> MicrosoftSyncResult:
        now = datetime.now(timezone.utc)
        initial = f"{GRAPH_URL}/me/calendarView/delta?startDateTime={self._rfc3339(now - timedelta(days=30))}&endDateTime={self._rfc3339(now + timedelta(days=90))}&$select=id,subject,start,end,showAs,isCancelled,recurrence,lastModifiedDateTime,location,attendees,iCalUId"
        rows, delta = await self._delta_incremental(account.sync_token, initial, access)
        existing = {row.provider_event_id: row for row in (await self.session.execute(select(CalendarEvent).where(CalendarEvent.user_id == account.user_id, CalendarEvent.provider == account.provider))).scalars()}
        contacts = {email.casefold(): contact for contact in (await self.session.execute(select(MicrosoftContact).where(MicrosoftContact.user_id == account.user_id, MicrosoftContact.deleted.is_(False)))).scalars() for email in contact.emails}
        result = MicrosoftSyncResult()
        for raw in rows:
            item_id = str(raw.get("id") or "")
            if not item_id:
                continue
            event = existing.get(item_id)
            created = event is None
            if event is None:
                event = CalendarEvent(user_id=account.user_id, connected_account_id=account.id, provider=account.provider, provider_event_id=item_id)
                self.session.add(event)
                existing[item_id] = event
            removed = bool(raw.get("@removed")) or bool(raw.get("isCancelled"))
            attendees = []
            for attendee in raw.get("attendees") or []:
                email = str(((attendee.get("emailAddress") or {}).get("address") or "")).lower()
                contact = contacts.get(email.casefold())
                attendees.append({"name": contact.display_name if contact else str((attendee.get("emailAddress") or {}).get("name") or email), "email": email, "company": contact.company if contact else None, "jobTitle": contact.job_title if contact else None})
            event.status = "cancelled" if removed else "confirmed"
            event.title = str(raw.get("subject") or event.title or "Busy")[:300]
            event.start_at = self._graph_datetime(raw.get("start")) or event.start_at
            event.end_at = self._graph_datetime(raw.get("end")) or event.end_at
            event.location = str(((raw.get("location") or {}).get("displayName") or ""))[:300]
            event.all_day = bool(raw.get("isAllDay"))
            event.recurring = bool(raw.get("recurrence"))
            event.busy = raw.get("showAs") not in {"free", "unknown"} and not removed
            event.i_cal_uid = raw.get("iCalUId")
            event.event_metadata = {"attendees": attendees, "lastModifiedDateTime": raw.get("lastModifiedDateTime")}
            result.cancelled += int(removed)
            result.synced += int(created and not removed)
            result.updated += int(not created and not removed)
        account.sync_token = delta or account.sync_token
        active = [event for event in existing.values() if event.status != "cancelled"]
        account.app_metadata = {**(account.app_metadata or {}), "events_count": len(active), "recurring_events_count": sum(1 for event in active if event.recurring)}
        return result

    async def _sync_drive(self, account: ConnectedAppAccount, access: str) -> MicrosoftSyncResult:
        initial = f"{GRAPH_URL}/me/drive/root/delta?$select=id,name,lastModifiedDateTime,file,shared,deleted"
        rows, delta = await self._delta_incremental(account.sync_token, initial, access)
        existing = {row.provider_item_id: row for row in (await self.session.execute(select(MicrosoftDriveItem).where(MicrosoftDriveItem.user_id == account.user_id))).scalars()}
        result = MicrosoftSyncResult()
        for raw in rows:
            if "folder" in raw:
                continue
            item_id = str(raw.get("id") or "")
            if not item_id:
                continue
            item = existing.get(item_id)
            created = item is None
            if item is None:
                item = MicrosoftDriveItem(user_id=account.user_id, connected_account_id=account.id, provider_item_id=item_id)
                self.session.add(item)
                existing[item_id] = item
            removed = bool(raw.get("deleted"))
            item.name = str(raw.get("name") or item.name or "")[:500]
            item.mime_type = str((raw.get("file") or {}).get("mimeType") or item.mime_type or "")[:240]
            item.modified_at = self._datetime(raw.get("lastModifiedDateTime")) or item.modified_at
            item.shared = bool(raw.get("shared"))
            item.deleted = removed
            result.cancelled += int(removed)
            result.synced += int(created and not removed)
            result.updated += int(not created and not removed)
        account.sync_token = delta or account.sync_token
        active = [item for item in existing.values() if not item.deleted]
        recent = sorted(active, key=lambda item: self._aware(item.modified_at or datetime.min), reverse=True)[:25]
        account.app_metadata = {**(account.app_metadata or {}), "recent_files_count": len(recent), "shared_files_count": sum(1 for item in recent if item.shared), "recent_file_names": [item.name for item in recent[:10]]}
        return result

    async def _sync_todo(self, account: ConnectedAppAccount, access: str) -> MicrosoftSyncResult:
        headers = {"Authorization": f"Bearer {access}"}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{GRAPH_URL}/me/todo/lists?$select=id,displayName", headers=headers)
        self._raise_graph(response, "Microsoft To Do")
        lists = response.json().get("value") or []
        stored_lists = {row.provider_list_id: row for row in (await self.session.execute(select(MicrosoftTaskList).where(MicrosoftTaskList.user_id == account.user_id))).scalars()}
        stored_tasks = {row.provider_task_id: row for row in (await self.session.execute(select(MicrosoftTask).where(MicrosoftTask.user_id == account.user_id))).scalars()}
        delta_links = dict((account.app_metadata or {}).get("task_delta_links") or {})
        result = MicrosoftSyncResult()
        for raw_list in lists:
            list_id = str(raw_list.get("id") or "")
            if not list_id:
                continue
            task_list = stored_lists.get(list_id)
            if task_list is None:
                task_list = MicrosoftTaskList(user_id=account.user_id, connected_account_id=account.id, provider_list_id=list_id)
                self.session.add(task_list)
                await self.session.flush()
                stored_lists[list_id] = task_list
            task_list.title = str(raw_list.get("displayName") or "")[:300]
            initial = f"{GRAPH_URL}/me/todo/lists/{list_id}/tasks/delta?$select=id,title,status,importance,dueDateTime,completedDateTime,recurrence,lastModifiedDateTime"
            rows, delta = await self._delta_incremental(delta_links.get(list_id), initial, access)
            if delta:
                delta_links[list_id] = delta
            for raw in rows:
                task_id = str(raw.get("id") or "")
                if not task_id:
                    continue
                task = stored_tasks.get(task_id)
                created = task is None
                if task is None:
                    task = MicrosoftTask(user_id=account.user_id, connected_account_id=account.id, task_list_id=task_list.id, provider_task_id=task_id)
                    self.session.add(task)
                    stored_tasks[task_id] = task
                removed = bool(raw.get("@removed"))
                task.task_list_id = task_list.id
                task.title = str(raw.get("title") or task.title or "")[:500]
                task.status = str(raw.get("status") or task.status or "notStarted")[:40]
                task.importance = str(raw.get("importance") or task.importance or "normal")[:40]
                task.due_at = self._graph_datetime(raw.get("dueDateTime")) or task.due_at
                task.completed_at = self._graph_datetime(raw.get("completedDateTime")) or task.completed_at
                task.recurrence = raw.get("recurrence") or task.recurrence or {}
                task.provider_updated_at = self._datetime(raw.get("lastModifiedDateTime")) or task.provider_updated_at
                task.deleted = removed
                result.cancelled += int(removed)
                result.synced += int(created and not removed)
                result.updated += int(not created and not removed)
        active = [task for task in stored_tasks.values() if not task.deleted and task.status != "completed"]
        now = datetime.now(timezone.utc)
        overdue = [task for task in active if task.due_at and self._aware(task.due_at) < now]
        account.app_metadata = {**(account.app_metadata or {}), "task_delta_links": delta_links, "task_lists_count": len(lists), "active_tasks_count": len(active), "completed_tasks_count": sum(1 for task in stored_tasks.values() if not task.deleted and task.status == "completed"), "overdue_tasks_count": len(overdue), "recurring_tasks_count": sum(1 for task in active if task.recurrence)}
        return result

    async def _sync_people(self, account: ConnectedAppAccount, access: str) -> MicrosoftSyncResult:
        initial = f"{GRAPH_URL}/me/contacts/delta?$select=id,displayName,emailAddresses,companyName,jobTitle,lastModifiedDateTime,categories"
        rows, delta = await self._delta_incremental(account.sync_token, initial, access)
        existing = {row.provider_contact_id: row for row in (await self.session.execute(select(MicrosoftContact).where(MicrosoftContact.user_id == account.user_id))).scalars()}
        result = MicrosoftSyncResult()
        for raw in rows:
            contact_id = str(raw.get("id") or "")
            if not contact_id:
                continue
            contact = existing.get(contact_id)
            created = contact is None
            if contact is None:
                contact = MicrosoftContact(user_id=account.user_id, connected_account_id=account.id, provider_contact_id=contact_id)
                self.session.add(contact)
                existing[contact_id] = contact
            removed = bool(raw.get("@removed"))
            contact.display_name = str(raw.get("displayName") or contact.display_name or "")[:300]
            contact.emails = list(dict.fromkeys(str(item.get("address") or "").lower() for item in raw.get("emailAddresses") or [] if item.get("address")))[:10]
            contact.company = str(raw.get("companyName") or contact.company or "")[:300]
            contact.job_title = str(raw.get("jobTitle") or contact.job_title or "")[:300]
            contact.relationship_metadata = {"categories": [str(value)[:120] for value in raw.get("categories") or []]} if raw.get("categories") else {}
            contact.provider_updated_at = self._datetime(raw.get("lastModifiedDateTime")) or contact.provider_updated_at
            contact.deleted = removed
            result.cancelled += int(removed)
            result.synced += int(created and not removed)
            result.updated += int(not created and not removed)
        account.sync_token = delta or account.sync_token
        active = [contact for contact in existing.values() if not contact.deleted]
        account.app_metadata = {**(account.app_metadata or {}), "contacts_count": len(active), "contacts_with_organization_count": sum(1 for contact in active if contact.company or contact.job_title), "contacts_with_relationship_count": sum(1 for contact in active if contact.relationship_metadata), "contact_name_by_email": {email: contact.display_name for contact in active if contact.display_name for email in contact.emails}}
        return result

    async def _sync_teams(self, account: ConnectedAppAccount, access: str) -> MicrosoftSyncResult:
        result = MicrosoftSyncResult()
        raw_teams = await self._graph_collection(f"{GRAPH_URL}/me/joinedTeams", access)
        existing_teams = {row.provider_team_id: row for row in (await self.session.execute(select(MicrosoftTeam).where(MicrosoftTeam.user_id == account.user_id))).scalars()}
        watermarks = dict((account.app_metadata or {}).get("channel_watermarks") or {})
        recent_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        all_members: dict[str, MicrosoftTeamMembership] = {}
        all_channels: set[str] = set()
        for raw_team in raw_teams:
            provider_team_id = str(raw_team.get("id") or "")
            if not provider_team_id:
                continue
            team = existing_teams.get(provider_team_id)
            created = team is None
            if team is None:
                team = MicrosoftTeam(user_id=account.user_id, connected_account_id=account.id, provider_team_id=provider_team_id)
                self.session.add(team)
                await self.session.flush()
                existing_teams[provider_team_id] = team
            team.display_name = str(raw_team.get("displayName") or team.display_name or "")[:300]
            team.description = str(raw_team.get("description") or team.description or "")[:2000]
            team.is_archived = bool(raw_team.get("isArchived"))
            result.synced += int(created)
            result.updated += int(not created)

            raw_channels = await self._graph_collection(f"{GRAPH_URL}/teams/{provider_team_id}/channels?$select=id,displayName,membershipType", access)
            channels = await self._upsert_team_channels(account, team, raw_channels)
            all_channels.update(channel.provider_channel_id for channel in channels)
            raw_members = await self._graph_collection(f"{GRAPH_URL}/teams/{provider_team_id}/members", access)
            members = await self._upsert_team_members(account, team, raw_members)
            all_members.update({member.provider_user_id: member for member in members})

            for channel in channels:
                if team.is_archived:
                    continue
                key = f"{provider_team_id}:{channel.provider_channel_id}"
                watermark = self._datetime(watermarks.get(key)) or recent_cutoff
                messages = await self._graph_collection(
                    f"{GRAPH_URL}/teams/{provider_team_id}/channels/{channel.provider_channel_id}/messages?$top=50",
                    access,
                )
                newest = watermark
                for raw in messages:
                    occurred = self._datetime(raw.get("lastModifiedDateTime") or raw.get("createdDateTime"))
                    if occurred and occurred <= watermark:
                        continue
                    is_new = await self._upsert_team_activity(account, team, channel, raw)
                    result.synced += int(is_new)
                    result.updated += int(not is_new)
                    if occurred and occurred > newest:
                        newest = occurred
                    channel.last_activity_at = max(filter(None, [self._aware(channel.last_activity_at) if channel.last_activity_at else None, occurred]), default=None)
                    team.last_activity_at = max(filter(None, [self._aware(team.last_activity_at) if team.last_activity_at else None, occurred]), default=None)
                watermarks[key] = self._rfc3339(newest)

        meetings = await self._graph_collection(
            f"{GRAPH_URL}/me/calendarView?startDateTime={self._rfc3339(recent_cutoff)}&endDateTime={self._rfc3339(datetime.now(timezone.utc) + timedelta(days=7))}&$select=id,subject,start,end,attendees,isOnlineMeeting,onlineMeetingProvider,lastModifiedDateTime",
            access,
        )
        for raw in meetings:
            if not raw.get("isOnlineMeeting") and raw.get("onlineMeetingProvider") != "teamsForBusiness":
                continue
            provider_id = f"meeting:{raw.get('id') or ''}"
            if provider_id == "meeting:":
                continue
            existing = (await self.session.execute(select(MicrosoftTeamsActivity).where(MicrosoftTeamsActivity.user_id == account.user_id, MicrosoftTeamsActivity.provider_activity_id == provider_id))).scalar_one_or_none()
            created = existing is None
            activity = existing or MicrosoftTeamsActivity(user_id=account.user_id, connected_account_id=account.id, provider_activity_id=provider_id)
            if created:
                self.session.add(activity)
            attendees = [str(((item.get("emailAddress") or {}).get("name") or ""))[:300] for item in raw.get("attendees") or []]
            activity.activity_type = "meeting"
            activity.participant_names = [name for name in attendees if name][:50]
            activity.occurred_at = self._graph_datetime(raw.get("start"))
            activity.activity_metadata = {
                "title": str(raw.get("subject") or "Teams meeting")[:300],
                "endAt": (raw.get("end") or {}).get("dateTime"),
                "participantCount": len(activity.participant_names),
            }
            result.synced += int(created)
            result.updated += int(not created)

        await self.session.flush()
        recent = list((await self.session.execute(select(MicrosoftTeamsActivity).where(MicrosoftTeamsActivity.user_id == account.user_id, MicrosoftTeamsActivity.occurred_at >= datetime.now(timezone.utc) - timedelta(days=7)))).scalars())
        account.app_metadata = {
            **(account.app_metadata or {}),
            "channel_watermarks": watermarks,
            "teams_count": len(existing_teams),
            "channel_count": len(all_channels),
            "member_count": len(all_members),
            "recent_activity_count": sum(row.activity_type == "channel_message" for row in recent),
            "recent_thread_count": len({row.reply_to_id for row in recent if row.reply_to_id}),
            "recent_meeting_count": sum(row.activity_type == "meeting" for row in recent),
            "mention_count": sum(bool(row.mention_user_ids) for row in recent),
            "blocker_signal_count": sum("blocker" in (row.signal_types or []) for row in recent),
            "decision_pending_count": sum("decision_pending" in (row.signal_types or []) for row in recent),
        }
        return result

    async def _upsert_team_channels(self, account: ConnectedAppAccount, team: MicrosoftTeam, rows: list[dict[str, Any]]) -> list[MicrosoftTeamChannel]:
        existing = {row.provider_channel_id: row for row in (await self.session.execute(select(MicrosoftTeamChannel).where(MicrosoftTeamChannel.team_id == team.id))).scalars()}
        for raw in rows:
            provider_id = str(raw.get("id") or "")
            if not provider_id:
                continue
            channel = existing.get(provider_id)
            if channel is None:
                channel = MicrosoftTeamChannel(user_id=account.user_id, connected_account_id=account.id, team_id=team.id, provider_channel_id=provider_id)
                self.session.add(channel)
                existing[provider_id] = channel
            channel.display_name = str(raw.get("displayName") or channel.display_name or "")[:300]
            channel.membership_type = str(raw.get("membershipType") or channel.membership_type or "standard")[:40]
        await self.session.flush()
        return list(existing.values())

    async def _upsert_team_members(self, account: ConnectedAppAccount, team: MicrosoftTeam, rows: list[dict[str, Any]]) -> list[MicrosoftTeamMembership]:
        existing = {row.provider_user_id: row for row in (await self.session.execute(select(MicrosoftTeamMembership).where(MicrosoftTeamMembership.team_id == team.id))).scalars()}
        for raw in rows:
            provider_id = str(raw.get("userId") or raw.get("id") or "")
            if not provider_id:
                continue
            member = existing.get(provider_id)
            if member is None:
                member = MicrosoftTeamMembership(user_id=account.user_id, connected_account_id=account.id, team_id=team.id, provider_user_id=provider_id)
                self.session.add(member)
                existing[provider_id] = member
            member.display_name = str(raw.get("displayName") or member.display_name or "")[:300]
            member.email = str(raw.get("email") or member.email or "").lower()[:320]
            member.roles = [str(role)[:80] for role in raw.get("roles") or []]
        await self.session.flush()
        return list(existing.values())

    async def _upsert_team_activity(self, account: ConnectedAppAccount, team: MicrosoftTeam, channel: MicrosoftTeamChannel, raw: dict[str, Any]) -> bool:
        raw_id = str(raw.get("id") or "")
        provider_id = f"message:{team.provider_team_id}:{channel.provider_channel_id}:{raw_id}"
        existing = (await self.session.execute(select(MicrosoftTeamsActivity).where(MicrosoftTeamsActivity.user_id == account.user_id, MicrosoftTeamsActivity.provider_activity_id == provider_id))).scalar_one_or_none()
        created = existing is None
        activity = existing or MicrosoftTeamsActivity(user_id=account.user_id, connected_account_id=account.id, provider_activity_id=provider_id)
        if created:
            self.session.add(activity)
        sender = ((raw.get("from") or {}).get("user") or {})
        mentions = [((item.get("mentioned") or {}).get("user") or {}) for item in raw.get("mentions") or []]
        transient_text = str(((raw.get("body") or {}).get("content") or ""))
        signals = []
        if TEAMS_SIGNAL_BLOCKER.search(transient_text):
            signals.append("blocker")
        if TEAMS_SIGNAL_DECISION.search(transient_text):
            signals.append("decision_pending")
        activity.team_id = team.id
        activity.channel_id = channel.id
        activity.activity_type = "channel_message"
        activity.author_provider_user_id = str(sender.get("id") or "")[:512]
        activity.author_display_name = str(sender.get("displayName") or "")[:300]
        activity.reply_to_id = str(raw.get("replyToId") or "")[:512]
        activity.mention_user_ids = [str(item.get("id") or "")[:512] for item in mentions if item.get("id")]
        activity.participant_names = [str(item.get("displayName") or "")[:300] for item in mentions if item.get("displayName")]
        activity.signal_types = signals
        activity.occurred_at = self._datetime(raw.get("lastModifiedDateTime") or raw.get("createdDateTime"))
        activity.activity_metadata = {"importance": str(raw.get("importance") or "normal")[:40], "mentionCount": len(activity.mention_user_ids)}
        return created

    async def _create_observations(self, account: ConnectedAppAccount) -> int:
        metadata = account.app_metadata or {}
        values: list[str] = []
        if account.provider == "microsoft_outlook_mail":
            if unread := int(metadata.get("unread_messages_count") or 0):
                values.append(f"Outlook evidence: {unread} unread message{'s are' if unread != 1 else ' is'} visible from metadata.")
            if waiting := int(metadata.get("waiting_for_reply_count") or 0):
                values.append(f"Outlook evidence: {waiting} conversation{'s appear' if waiting != 1 else ' appears'} to be waiting for a reply.")
        elif account.provider == "microsoft_outlook_calendar":
            if events := int(metadata.get("events_count") or 0):
                values.append(f"Outlook Calendar evidence: {events} active event{'s are' if events != 1 else ' is'} visible in the sync window.")
        elif account.provider == "microsoft_onedrive":
            if recent := int(metadata.get("recent_files_count") or 0):
                values.append(f"OneDrive evidence: {recent} recently active file{'s may' if recent != 1 else ' may'} reflect current work.")
        elif account.provider == "microsoft_todo":
            if overdue := int(metadata.get("overdue_tasks_count") or 0):
                values.append(f"Microsoft To Do evidence: {overdue} active task{'s are' if overdue != 1 else ' is'} overdue.")
            if completed := int(metadata.get("completed_tasks_count") or 0):
                values.append(f"Microsoft To Do evidence: {completed} synced task{'s are' if completed != 1 else ' is'} completed.")
        elif account.provider == "microsoft_teams":
            if activity := int(metadata.get("recent_activity_count") or 0):
                values.append(f"Microsoft Teams evidence: {activity} recent channel activit{'ies show' if activity != 1 else 'y shows'} active team discussion.")
            if blockers := int(metadata.get("blocker_signal_count") or 0):
                values.append(f"Microsoft Teams evidence: {blockers} recent activit{'ies used' if blockers != 1 else 'y used'} blocker or waiting language.")
            if decisions := int(metadata.get("decision_pending_count") or 0):
                values.append(f"Microsoft Teams evidence: {decisions} recent activit{'ies indicated' if decisions != 1 else 'y indicated'} a pending decision.")
            if meetings := int(metadata.get("recent_meeting_count") or 0):
                values.append(f"Microsoft Teams evidence: {meetings} meeting{'s were' if meetings != 1 else ' was'} visible in the recent collaboration window.")
            activities = list((await self.session.execute(select(MicrosoftTeamsActivity).where(MicrosoftTeamsActivity.user_id == account.user_id, MicrosoftTeamsActivity.occurred_at >= datetime.now(timezone.utc) - timedelta(days=14)))).scalars())
            collaborator_counts = Counter(name for row in activities for name in (row.participant_names or []) if name)
            for name, count in collaborator_counts.most_common(3):
                if count >= 3:
                    values.append(f"Microsoft Teams evidence: recent synced activity shows frequent collaboration with {name} ({count} interactions).")
        else:
            contacts = list((await self.session.execute(select(MicrosoftContact).where(MicrosoftContact.user_id == account.user_id, MicrosoftContact.deleted.is_(False)))).scalars())
            for contact in contacts:
                evidence = [value for value in [*(contact.relationship_metadata or {}).get("categories", [])[:2], contact.job_title, contact.company] if value]
                if contact.display_name and evidence:
                    values.append(f"Microsoft People evidence: {contact.display_name} — {', '.join(evidence)}.")
        existing = {row.content for row in (await self.session.execute(select(LearningObservation).where(LearningObservation.user_id == account.user_id, LearningObservation.source == account.provider))).scalars()}
        created = 0
        for content in values:
            if content not in existing:
                self.session.add(LearningObservation(user_id=account.user_id, source=account.provider, content=content, status="observed"))
                created += 1
        await self.session.flush()
        return created

    async def _graph_collection(self, url: str, access: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        headers = {"Authorization": f"Bearer {access}", "Prefer": "odata.maxpagesize=100"}
        async with httpx.AsyncClient(timeout=25) as client:
            next_url: str | None = url
            while next_url:
                response = await client.get(next_url, headers=headers)
                self._raise_graph(response, "Microsoft Teams")
                payload = response.json()
                rows.extend(payload.get("value") or [])
                next_url = payload.get("@odata.nextLink")
        return rows

    async def _delta(self, url: str, access: str) -> tuple[list[dict[str, Any]], str | None]:
        rows: list[dict[str, Any]] = []
        delta: str | None = None
        headers = {"Authorization": f"Bearer {access}", "Prefer": "odata.maxpagesize=250"}
        async with httpx.AsyncClient(timeout=25) as client:
            next_url: str | None = url
            while next_url:
                response = await client.get(next_url, headers=headers)
                self._raise_graph(response, "Microsoft Graph")
                payload = response.json()
                rows.extend(payload.get("value") or [])
                next_url = payload.get("@odata.nextLink")
                delta = payload.get("@odata.deltaLink") or delta
        return rows, delta

    async def _delta_incremental(self, current: str | None, initial: str, access: str) -> tuple[list[dict[str, Any]], str | None]:
        try:
            return await self._delta(current or initial, access)
        except AppError as exc:
            if current and exc.code == "microsoft_delta_expired":
                return await self._delta(initial, access)
            raise

    async def _exchange_code(self, code: str, spec: MicrosoftProviderSpec) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(self._token_url(), data={"client_id": self.settings.microsoft_client_id, "client_secret": self.settings.microsoft_client_secret, "code": code, "redirect_uri": self._redirect_uri(), "grant_type": "authorization_code", "scope": " ".join(spec.scopes)})
        if response.status_code >= 400:
            raise AppError("Microsoft OAuth exchange failed", status_code=400, code="oauth_exchange_failed", user_message=f"{spec.label} could not complete authorization.")
        return response.json()

    async def _load_profile(self, account: ConnectedAppAccount, access: str) -> None:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"{GRAPH_URL}/me?$select=id,displayName,mail,userPrincipalName", headers={"Authorization": f"Bearer {access}"})
        self._raise_graph(response, "Microsoft profile")
        profile = response.json()
        account.provider_account_id = str(profile.get("id") or "")[:240] or None
        account.app_metadata = {**(account.app_metadata or {}), "account_email": str(profile.get("mail") or profile.get("userPrincipalName") or "").lower(), "account_name": str(profile.get("displayName") or "")[:300]}

    async def _set_error(self, account: ConnectedAppAccount, code: str, message: str, status: str = "error") -> None:
        account.status = status
        account.last_error_code = code
        account.last_error_message = message
        await self.session.flush()

    def _status_out(self, spec: MicrosoftProviderSpec, account: ConnectedAppAccount | None) -> dict:
        status = account.status if account else "not_connected"
        return {"provider": spec.provider, "status": status, "connected": status == "connected", "lastSyncedAt": account.last_synced_at if account else None, "lastErrorCode": account.last_error_code if account else None, "lastErrorMessage": account.last_error_message if account else None, "permissions": [spec.permission] if account and account.scopes else [], "scopes": account.scopes if account else [], "privacy": {"why": spec.why, "reads": spec.reads, "usage": spec.usage, "ignored": spec.ignored}}

    def _encode_state(self, user_id: UUID, provider: str) -> str:
        return jwt.encode({"sub": str(user_id), "provider": provider, "nonce": secrets.token_urlsafe(12), "exp": datetime.now(timezone.utc) + timedelta(minutes=15), "type": "microsoft_365_oauth_state"}, self.settings.jwt_secret_key, algorithm=self.settings.jwt_algorithm)

    def _decode_state(self, state: str) -> tuple[UUID, str]:
        try:
            payload = jwt.decode(state, self.settings.jwt_secret_key, algorithms=[self.settings.jwt_algorithm])
            provider = str(payload.get("provider") or "")
            if payload.get("type") != "microsoft_365_oauth_state" or provider not in MICROSOFT_PROVIDERS:
                raise ValueError
            return UUID(str(payload["sub"])), provider
        except (JWTError, ValueError, KeyError) as exc:
            raise AppError("Invalid Microsoft OAuth state", status_code=400, code="invalid_oauth_state") from exc

    def _state_nonce(self, state: str) -> str:
        try:
            payload = jwt.decode(state, self.settings.jwt_secret_key, algorithms=[self.settings.jwt_algorithm])
            return str(payload["nonce"])
        except (JWTError, KeyError, TypeError) as exc:
            raise AppError("Invalid Microsoft OAuth state", status_code=400, code="invalid_oauth_state") from exc

    def _require_config(self, spec: MicrosoftProviderSpec) -> None:
        if not self.settings.microsoft_client_id or not self.settings.microsoft_client_secret:
            raise AppError(f"{spec.label} is not configured", status_code=503, code="microsoft_365_not_configured", user_message="Microsoft 365 is not configured for this Synzept environment yet.")

    def _spec(self, provider: str) -> MicrosoftProviderSpec:
        try:
            return MICROSOFT_PROVIDERS[provider]
        except KeyError as exc:
            raise AppError("Unsupported Microsoft provider", status_code=404, code="unsupported_microsoft_provider") from exc

    def _authorize_url(self) -> str:
        return AUTHORIZE_URL.format(tenant=self.settings.microsoft_tenant_id or "common")

    def _token_url(self) -> str:
        return TOKEN_URL.format(tenant=self.settings.microsoft_tenant_id or "common")

    def _redirect_uri(self) -> str:
        return self.settings.microsoft_redirect_uri or f"{self.settings.frontend_url.rstrip('/').replace('localhost:3000', 'localhost:8000')}/api/connected-apps/microsoft/callback"

    @staticmethod
    def _raise_graph(response: httpx.Response, label: str) -> None:
        if response.status_code == 401:
            raise AppError(f"{label} permission expired", status_code=409, code="permission_revoked", user_message=f"{label} authorization expired. Reconnect to continue.")
        if response.status_code == 403:
            raise AppError(f"{label} permission denied", status_code=403, code="microsoft_permission_denied", user_message=f"{label} does not have the required read permission.")
        if response.status_code == 429:
            raise AppError(f"{label} rate limited", status_code=429, code="microsoft_rate_limited", user_message="Microsoft asked Synzept to slow down. Try syncing again later.")
        if response.status_code == 410:
            raise AppError(f"{label} delta expired", status_code=410, code="microsoft_delta_expired", user_message="Microsoft sync state expired; Synzept will safely rebuild it.")
        if response.status_code >= 500:
            raise AppError(f"{label} unavailable", status_code=503, code="microsoft_unavailable", user_message="Microsoft Graph is unavailable right now.")
        if response.status_code >= 400:
            raise AppError(f"{label} sync failed", status_code=400, code="sync_failed", user_message=f"{label} sync failed.")

    @staticmethod
    def _datetime(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    @classmethod
    def _graph_datetime(cls, value: Any) -> datetime | None:
        return cls._datetime((value or {}).get("dateTime") if isinstance(value, dict) else value)

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _rfc3339(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _day_start(value: date) -> datetime:
        return datetime.combine(value, time.min, tzinfo=timezone.utc)

    @staticmethod
    def _duration(event: CalendarEvent) -> int:
        return max(0, round(((event.end_at or event.start_at) - event.start_at).total_seconds() / 60)) if event.start_at else 0

    @classmethod
    def _conflicts(cls, events: list[CalendarEvent]) -> list[str]:
        conflicts = []
        ordered = sorted([event for event in events if event.busy and event.start_at and event.end_at], key=lambda event: event.start_at)
        for current, following in zip(ordered, ordered[1:]):
            if current.end_at and following.start_at and following.start_at < current.end_at:
                conflicts.append(f"{current.title} overlaps with {following.title}.")
        return conflicts

    @classmethod
    def _free_blocks(cls, events: list[CalendarEvent]) -> list[dict]:
        cursor = datetime.combine(date.today(), time(9), tzinfo=timezone.utc)
        end = datetime.combine(date.today(), time(18), tzinfo=timezone.utc)
        blocks = []
        for event in sorted([event for event in events if event.busy and event.start_at and event.end_at], key=lambda event: event.start_at):
            start_at = cls._aware(event.start_at)
            end_at = cls._aware(event.end_at)
            if start_at > cursor and (minutes := round((start_at - cursor).total_seconds() / 60)) >= 45:
                blocks.append({"startAt": cursor, "endAt": start_at, "minutes": minutes})
            if end_at > cursor:
                cursor = end_at
        if cursor < end and (minutes := round((end - cursor).total_seconds() / 60)) >= 45:
            blocks.append({"startAt": cursor, "endAt": end, "minutes": minutes})
        return blocks

    @staticmethod
    def _calendar_item(event: CalendarEvent) -> dict:
        return {"title": event.title, "startAt": event.start_at, "endAt": event.end_at, "status": event.status, "recurring": event.recurring, "busy": event.busy, "people": (event.event_metadata or {}).get("attendees", [])}
