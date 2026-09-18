from __future__ import annotations

import base64
import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError
from app.models.connected_app import ConnectedAppAccount, GoogleContact, GoogleTask, GoogleTaskList
from app.models.learning import LearningObservation
from app.models.user import User
from app.services.connected_apps.oauth_lifecycle import ConnectedAppOAuthLifecycle

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GMAIL_MESSAGES_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
GMAIL_LABELS_URL = "https://gmail.googleapis.com/gmail/v1/users/me/labels"
DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
TASK_LISTS_URL = "https://tasks.googleapis.com/tasks/v1/users/@me/lists"
TASKS_URL = "https://tasks.googleapis.com/tasks/v1/lists/{task_list_id}/tasks"
CONTACTS_URL = "https://people.googleapis.com/v1/people/me/connections"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GoogleServiceSpec:
    provider: str
    label: str
    scope: str
    permission: str
    why: str
    reads: str
    usage: str
    ignored: str


GOOGLE_SERVICES: dict[str, GoogleServiceSpec] = {
    "google_gmail": GoogleServiceSpec(
        provider="google_gmail",
        label="Gmail",
        scope="https://www.googleapis.com/auth/gmail.readonly",
        permission="Read and send Gmail messages after approval",
        why="Gmail helps Synzept find messages that need a response and prepare replies for your review.",
        reads="Message headers, snippets, labels, thread IDs, and the limited message context needed to draft a reply.",
        usage="Synzept prepares drafts first. Sending a reply always requires your explicit approval.",
        ignored="Synzept does not send, edit, or delete mail without explicit approval.",
    ),
    "google_drive": GoogleServiceSpec(
        provider="google_drive",
        label="Google Drive",
        scope="https://www.googleapis.com/auth/drive.metadata.readonly",
        permission="Read Drive metadata",
        why="Drive helps Synzept notice active documents, project activity, and files you return to often.",
        reads="File names, MIME type, timestamps, owners, and lightweight file metadata.",
        usage="Drive metadata becomes observations first and requires approval before changing understanding.",
        ignored="Synzept does not read document contents, download files, edit files, or change sharing.",
    ),
    "google_tasks": GoogleServiceSpec(
        provider="google_tasks",
        label="Google Tasks",
        scope="https://www.googleapis.com/auth/tasks.readonly",
        permission="View your tasks and task lists",
        why="Tasks help Synzept notice active work, open loops, completion patterns, and realistic priorities.",
        reads="Task names, task lists, due dates, completion status, hierarchy, position, and update timestamps.",
        usage="Task evidence improves Today, Think, and Weekly Review through observations that require approval before changing understanding.",
        ignored="Synzept does not create, edit, delete, reorder, or complete tasks. Task notes are not read.",
    ),
    "google_contacts": GoogleServiceSpec(
        provider="google_contacts",
        label="Google Contacts",
        scope="https://www.googleapis.com/auth/contacts.readonly",
        permission="View your contacts",
        why="Contacts help Synzept resolve names and understand explicit relationship context around collaboration.",
        reads="Contact names, email addresses, company, job title, explicit relationship metadata, and update timestamps.",
        usage="Contact evidence improves people-aware recommendations through observations that require approval before changing understanding.",
        ignored="Synzept does not read profile photos, send email, edit or delete contacts, or share contacts.",
    ),
    "google_docs": GoogleServiceSpec("google_docs", "Google Docs", "https://www.googleapis.com/auth/documents", "Edit Google Docs", "Docs deliverables are created and updated in your workspace.", "Document content required for the requested work.", "Documents are only changed for an explicit user outcome.", "Synzept does not share documents without approval."),
    "google_sheets": GoogleServiceSpec("google_sheets", "Google Sheets", "https://www.googleapis.com/auth/spreadsheets", "Edit Google Sheets", "Sheets support structured analysis and deliverables.", "Cells and formatting required for the requested work.", "Sheets are only changed for an explicit user outcome.", "Synzept does not share sheets without approval."),
    "google_slides": GoogleServiceSpec("google_slides", "Google Slides", "https://www.googleapis.com/auth/presentations", "Edit Google Slides", "Slides support presentations and briefing deliverables.", "Slides and speaker notes required for the requested work.", "Presentations are only changed for an explicit user outcome.", "Synzept does not share presentations without approval."),
}


@dataclass
class WorkspaceSyncResult:
    synced: int = 0
    updated: int = 0
    cancelled: int = 0
    observations: int = 0
    status: str = "connected"


class GoogleWorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self.oauth = ConnectedAppOAuthLifecycle(session)

    async def status(self, provider: str, user_id: UUID) -> dict:
        spec = self._spec(provider)
        return self._status_out(spec, await self._account(user_id, spec.provider))

    async def statuses(self, user_id: UUID) -> list[dict]:
        return [await self.status(provider, user_id) for provider in GOOGLE_SERVICES]

    async def authorization_url(self, provider: str, user: User) -> dict:
        spec = self._spec(provider)
        self._require_config(spec)
        logger.info("Google Workspace lifecycle provider requested provider=%s user_id=%s", spec.provider, user.id)
        account = await self._account(user.id, spec.provider)
        if account:
            account.status = "connecting"
            account.last_error_code = None
            account.last_error_message = None
        else:
            account = ConnectedAppAccount(user_id=user.id, provider=spec.provider, status="connecting", scopes=[spec.scope])
            self.session.add(account)
        state = self._encode_state(user.id, spec.provider)
        account.app_metadata = {**(account.app_metadata or {}), "oauth_state_nonce": self._state_nonce(state)}
        await self.session.flush()
        logger.info("Google Workspace lifecycle provider in OAuth state provider=%s user_id=%s", spec.provider, user.id)
        params = {
            "client_id": self.settings.google_connected_apps_client_id,
            "redirect_uri": self._redirect_uri(),
            "response_type": "code",
            "scope": spec.scope,
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
        }
        return {"authorizationUrl": f"{AUTH_URL}?{urlencode(params)}"}

    async def handle_callback(self, code: str | None, state: str | None, error: str | None, expected_user_id: UUID | None = None) -> str:
        frontend = self.settings.frontend_url.rstrip("/")
        provider = self.callback_provider(state)
        spec = self._spec(provider or "")
        self._require_config(spec)
        logger.info(
            "Google Workspace lifecycle provider in callback provider=%s code_present=%s error_present=%s",
            spec.provider,
            bool(code),
            bool(error),
        )

        if error:
            user_id, state_provider = self._decode_state(state or "")
            if expected_user_id is not None and user_id != expected_user_id:
                raise AppError("Invalid Google OAuth state", status_code=400, code="invalid_oauth_state")
            spec = self._spec(state_provider)
            await self._consume_state_nonce(user_id, self._state_nonce(state or ""), spec.provider)
            logger.warning(
                "Google Workspace OAuth callback returned an error provider=%s user_id=%s error=%s",
                spec.provider,
                user_id,
                error,
            )
            account = await self._account(user_id, spec.provider)
            if (
                error == "access_denied"
                and spec.provider == "google_contacts"
                and account
                and account.encrypted_refresh_token
                and spec.scope in account.scopes
            ):
                account.status = "connected"
                account.last_error_code = None
                account.last_error_message = None
                await self.session.flush()
                return f"{frontend}/connected?googleWorkspace=connected&googleService={spec.provider}"
            await self._mark_error(user_id, spec, "oauth_cancelled", f"Google {spec.label} connection was cancelled before permission was granted.")
            return f"{frontend}/connected?googleService={spec.provider}&googleWorkspace=cancelled"
        if not state:
            return f"{frontend}/connected?googleService={spec.provider}&googleWorkspace=error"

        user_id, state_provider = self._decode_state(state)
        if expected_user_id is not None and user_id != expected_user_id:
            raise AppError("Invalid Google OAuth state", status_code=400, code="invalid_oauth_state")
        spec = self._spec(state_provider)
        await self._consume_state_nonce(user_id, self._state_nonce(state), spec.provider)
        account = await self._ensure_account(user_id, spec.provider, spec.scope)
        if not code:
            await self._set_account_error(account, "oauth_missing_code", f"Google {spec.label} did not return an authorization code.")
            return f"{frontend}/connected?googleService={spec.provider}&googleWorkspace=error"
        try:
            tokens = await self._exchange_code(spec, code)
        except AppError as exc:
            logger.exception(
                "Google Workspace OAuth callback failed provider=%s user_id=%s error_code=%s redirect_uri=%s client_id=%s scopes=%s",
                spec.provider,
                user_id,
                exc.code,
                self._redirect_uri(),
                self._masked_client_id(),
                [spec.scope],
            )
            await self._set_account_error(account, "oauth_exchange_failed", f"Google {spec.label} did not complete the connection. Try again.")
            params = {"googleWorkspace": "error", "googleService": spec.provider}
            if self._is_development():
                params["googleWorkspaceError"] = self._safe_development_error(exc)
            return f"{frontend}/connected?{urlencode(params)}"

        refresh_token = tokens.get("refresh_token")
        if not refresh_token and account.encrypted_refresh_token:
            refresh_token = self._decrypt(account.encrypted_refresh_token)
        if not refresh_token:
            await self._set_account_error(account, "missing_refresh_token", f"Google {spec.label} did not return offline access. Reconnect and approve access again.")
            return f"{frontend}/connected?googleWorkspace=reconnect&googleService={spec.provider}"

        account.encrypted_refresh_token = self._encrypt(refresh_token)
        account.encrypted_access_token = self._encrypt(str(tokens.get("access_token") or ""))
        account.access_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(tokens.get("expires_in") or 3600) - 60)
        account.scopes = sorted(set(str(tokens.get("scope") or spec.scope).split()))
        if spec.scope not in account.scopes:
            message = f"Google {spec.label} did not grant the requested scope: {spec.scope}."
            await self._set_account_error(account, "oauth_missing_scope", message)
            logger.error(
                "Google Workspace OAuth missing requested scope provider=%s user_id=%s requested_scope=%s returned_scopes=%s",
                spec.provider,
                user_id,
                spec.scope,
                account.scopes,
            )
            return f"{frontend}/connected?{urlencode({'googleWorkspace': 'error', 'googleService': spec.provider, 'googleWorkspaceError': message} if self._is_development() else {'googleWorkspace': 'error', 'googleService': spec.provider})}"
        account.status = "connected"
        account.last_error_code = None
        account.last_error_message = None
        account.app_metadata = {**(account.app_metadata or {}), "connected_at": datetime.now(timezone.utc).isoformat()}
        await self.session.flush()
        logger.info(
            "Google Workspace lifecycle provider stored in database provider=%s user_id=%s status=%s scopes=%s",
            spec.provider,
            user_id,
            account.status,
            account.scopes,
        )
        logger.info("Google Workspace service connected provider=%s user_id=%s", spec.provider, user_id)

        try:
            await self.sync(spec.provider, user_id)
        except Exception:
            logger.exception("Google Workspace first sync failed provider=%s user_id=%s", spec.provider, user_id)
            account.status = "error"
            account.last_error_code = "sync_failed"
            account.last_error_message = f"Google {spec.label} connected, but the first sync did not complete. Try manual sync."
        return f"{frontend}/connected?googleWorkspace=connected&googleService={spec.provider}"

    async def sync(self, provider: str, user_id: UUID) -> WorkspaceSyncResult:
        spec = self._spec(provider)
        account = await self._required_account(user_id, spec.provider)
        logger.info("Google Workspace lifecycle status before sync provider=%s user_id=%s status=%s", spec.provider, user_id, account.status)
        if not account.encrypted_refresh_token:
            await self._set_account_error(account, "permission_revoked", f"Google {spec.label} needs to be reconnected.", status="permission_revoked")
            logger.info("Google Workspace lifecycle status after sync provider=%s user_id=%s status=%s", spec.provider, user_id, account.status)
            return WorkspaceSyncResult(status="permission_revoked")

        account.status = "syncing"
        await self.session.flush()
        try:
            access_token = await self._valid_access_token(account, spec)
            if spec.provider == "google_gmail":
                result = await self._sync_gmail(account, access_token)
            elif spec.provider == "google_drive":
                result = await self._sync_drive(account, access_token)
            elif spec.provider == "google_tasks":
                result = await self._sync_tasks(account, access_token)
            elif spec.provider == "google_contacts":
                result = await self._sync_contacts(account, access_token)
            else:
                result = WorkspaceSyncResult(status="connected")
            result.observations = await self._create_observations(account)
            account.status = "connected"
            account.last_synced_at = datetime.now(timezone.utc)
            account.last_error_code = None
            account.last_error_message = None
            await self.session.flush()
            logger.info("Google Workspace sync completed provider=%s user_id=%s synced=%s observations=%s", spec.provider, user_id, result.synced, result.observations)
            logger.info("Google Workspace lifecycle status after sync provider=%s user_id=%s status=%s", spec.provider, user_id, account.status)
            return result
        except (AppError, httpx.TimeoutException, httpx.RequestError) as exc:
            code = exc.code if isinstance(exc, AppError) else "provider_unavailable"
            status = "permission_revoked" if code in {"permission_revoked", "token_expired"} else "error"
            message = exc.user_message if isinstance(exc, AppError) else f"Google {spec.label} is unavailable right now. Try again later."
            await self._set_account_error(account, code, message, status=status)
            logger.exception("Google Workspace sync failed provider=%s user_id=%s error_code=%s", spec.provider, user_id, code)
            logger.info("Google Workspace lifecycle status after sync provider=%s user_id=%s status=%s", spec.provider, user_id, account.status)
            return WorkspaceSyncResult(status=status)

    async def disconnect(self, provider: str, user_id: UUID) -> dict:
        spec = self._spec(provider)
        account = await self._required_account(user_id, spec.provider)
        token = self._try_decrypt(account.encrypted_refresh_token) or self._try_decrypt(account.encrypted_access_token)
        if token:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(REVOKE_URL, params={"token": token})
            except httpx.RequestError:
                logger.warning("Google Workspace token revocation request failed; clearing local credentials provider=%s", spec.provider)
        account.status = "not_connected"
        account.encrypted_refresh_token = None
        account.encrypted_access_token = None
        account.access_token_expires_at = None
        account.sync_token = None
        account.last_error_code = None
        account.last_error_message = None
        await self.session.flush()
        logger.info("Google Workspace service disconnected provider=%s user_id=%s", spec.provider, user_id)
        return self._status_out(spec, account)

    async def _sync_gmail(self, account: ConnectedAppAccount, access_token: str) -> WorkspaceSyncResult:
        headers = {"Authorization": f"Bearer {access_token}"}
        sampled_params = {"maxResults": 25, "fields": "messages/id,messages/threadId,nextPageToken,resultSizeEstimate"}
        unread_params = {"maxResults": 10, "labelIds": "UNREAD", "fields": "messages/id,messages/threadId,resultSizeEstimate"}
        label_params = {"fields": "labels(id,name,type,messagesTotal,messagesUnread,threadsTotal,threadsUnread)"}
        async with httpx.AsyncClient(timeout=20) as client:
            logger.info("Google Workspace first Gmail API request provider=%s user_id=%s url=%s params=%s", account.provider, account.user_id, GMAIL_MESSAGES_URL, sampled_params)
            sampled = await client.get(GMAIL_MESSAGES_URL, params=sampled_params, headers=headers)
            if sampled.status_code >= 400:
                logger.error(
                    "Google Workspace first Gmail API request failed provider=%s user_id=%s url=%s params=%s status=%s response_body=%s",
                    account.provider,
                    account.user_id,
                    GMAIL_MESSAGES_URL,
                    sampled_params,
                    sampled.status_code,
                    self._safe_response_body(sampled),
                )
            unread = await client.get(GMAIL_MESSAGES_URL, params=unread_params, headers=headers)
            labels = await client.get(GMAIL_LABELS_URL, params=label_params, headers=headers)
        self._raise_for_google_api(sampled, "Gmail")
        self._raise_for_google_api(unread, "Gmail")
        self._raise_for_google_api(labels, "Gmail")
        sampled_payload = sampled.json()
        unread_payload = unread.json()
        label_payload = labels.json()
        label_counts = self._gmail_label_counts(label_payload.get("labels") or [])
        account.app_metadata = {
            **(account.app_metadata or {}),
            "mailbox_messages_estimate": int(sampled_payload.get("resultSizeEstimate") or 0),
            "unread_messages_estimate": int(unread_payload.get("resultSizeEstimate") or 0),
            "sampled_message_ids": [item.get("id") for item in (sampled_payload.get("messages") or [])[:10] if item.get("id")],
            "sampled_thread_ids": [item.get("threadId") for item in (sampled_payload.get("messages") or [])[:10] if item.get("threadId")],
            "gmail_label_counts": label_counts,
        }
        return WorkspaceSyncResult(synced=len(account.app_metadata.get("sampled_message_ids", [])))

    async def _sync_drive(self, account: ConnectedAppAccount, access_token: str) -> WorkspaceSyncResult:
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "pageSize": 25,
            "orderBy": "modifiedTime desc",
            "fields": "files(id,name,mimeType,modifiedTime,shared,owners/displayName)",
            "q": "trashed = false",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(DRIVE_FILES_URL, params=params, headers=headers)
        self._raise_for_google_api(response, "Drive")
        files = response.json().get("files") or []
        account.app_metadata = {
            **(account.app_metadata or {}),
            "recent_files_count": len(files),
            "shared_files_count": sum(1 for item in files if item.get("shared")),
            "recent_file_types": [str(item.get("mimeType") or "file") for item in files[:10]],
            "recent_file_names": [str(item.get("name") or "Untitled")[:120] for item in files[:10]],
        }
        return WorkspaceSyncResult(synced=len(files))

    async def _sync_tasks(self, account: ConnectedAppAccount, access_token: str) -> WorkspaceSyncResult:
        headers = {"Authorization": f"Bearer {access_token}"}
        list_items: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=20) as client:
            page_token: str | None = None
            while True:
                params: dict[str, Any] = {"maxResults": 100, "fields": "items(id,title,updated),nextPageToken"}
                if page_token:
                    params["pageToken"] = page_token
                response = await client.get(TASK_LISTS_URL, params=params, headers=headers)
                self._raise_for_google_api(response, "Tasks")
                payload = response.json()
                list_items.extend(payload.get("items") or [])
                page_token = payload.get("nextPageToken")
                if not page_token:
                    break

            stored_lists = {
                row.provider_list_id: row
                for row in (
                    await self.session.execute(select(GoogleTaskList).where(GoogleTaskList.user_id == account.user_id))
                ).scalars()
            }
            stored_tasks = {
                row.provider_task_id: row
                for row in (
                    await self.session.execute(select(GoogleTask).where(GoogleTask.user_id == account.user_id))
                ).scalars()
            }
            sync_watermarks = dict((account.app_metadata or {}).get("task_updated_min") or {})
            next_watermarks = dict(sync_watermarks)
            synced = updated = cancelled = 0
            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            for item in list_items:
                provider_list_id = str(item.get("id") or "")
                if not provider_list_id:
                    continue
                task_list = stored_lists.get(provider_list_id)
                if task_list is None:
                    task_list = GoogleTaskList(
                        user_id=account.user_id,
                        connected_account_id=account.id,
                        provider_list_id=provider_list_id,
                    )
                    self.session.add(task_list)
                    await self.session.flush()
                    stored_lists[provider_list_id] = task_list
                task_list.title = str(item.get("title") or "")[:300]
                task_list.provider_updated_at = self._google_datetime(item.get("updated"))

                page_token = None
                while True:
                    params = {
                        "maxResults": 100,
                        "showCompleted": "true",
                        "showDeleted": "true",
                        "showHidden": "true",
                        "fields": "items(id,title,status,due,completed,updated,parent,position,deleted),nextPageToken",
                    }
                    if sync_watermarks.get(provider_list_id):
                        params["updatedMin"] = sync_watermarks[provider_list_id]
                    if page_token:
                        params["pageToken"] = page_token
                    response = await client.get(TASKS_URL.format(task_list_id=provider_list_id), params=params, headers=headers)
                    self._raise_for_google_api(response, "Tasks")
                    payload = response.json()
                    for raw in payload.get("items") or []:
                        provider_task_id = str(raw.get("id") or "")
                        if not provider_task_id:
                            continue
                        task = stored_tasks.get(provider_task_id)
                        created = task is None
                        if task is None:
                            task = GoogleTask(
                                user_id=account.user_id,
                                connected_account_id=account.id,
                                task_list_id=task_list.id,
                                provider_task_id=provider_task_id,
                            )
                            self.session.add(task)
                            stored_tasks[provider_task_id] = task
                        task.task_list_id = task_list.id
                        task.provider_parent_id = str(raw.get("parent") or "") or None
                        task.title = str(raw.get("title") or "")[:500]
                        task.status = str(raw.get("status") or "needsAction")[:40]
                        task.due_at = self._google_datetime(raw.get("due"))
                        task.completed_at = self._google_datetime(raw.get("completed"))
                        task.provider_updated_at = self._google_datetime(raw.get("updated"))
                        task.position = str(raw.get("position") or "")[:128]
                        task.deleted = bool(raw.get("deleted"))
                        if task.deleted:
                            cancelled += 1
                        elif created:
                            synced += 1
                        else:
                            updated += 1
                    page_token = payload.get("nextPageToken")
                    if not page_token:
                        break
                next_watermarks[provider_list_id] = now_iso

        active = [task for task in stored_tasks.values() if not task.deleted and task.status != "completed"]
        completed = [task for task in stored_tasks.values() if not task.deleted and task.status == "completed"]
        now = datetime.now(timezone.utc)
        overdue = [task for task in active if task.due_at and self._aware_datetime(task.due_at) < now]
        due_today = [task for task in active if task.due_at and self._aware_datetime(task.due_at).date() == now.date()]
        account.app_metadata = {
            **(account.app_metadata or {}),
            "task_updated_min": next_watermarks,
            "task_lists_count": len(list_items),
            "active_tasks_count": len(active),
            "completed_tasks_count": len(completed),
            "overdue_tasks_count": len(overdue),
            "due_today_tasks_count": len(due_today),
            "active_task_titles": [task.title for task in sorted(active, key=lambda row: (row.due_at is None, row.due_at or now))[:10]],
        }
        return WorkspaceSyncResult(synced=synced, updated=updated, cancelled=cancelled)

    async def _sync_contacts(self, account: ConnectedAppAccount, access_token: str) -> WorkspaceSyncResult:
        headers = {"Authorization": f"Bearer {access_token}"}
        contacts = {
            row.resource_name: row
            for row in (
                await self.session.execute(select(GoogleContact).where(GoogleContact.user_id == account.user_id))
            ).scalars()
        }
        synced = updated = cancelled = 0
        sync_token = account.sync_token
        retried_full_sync = False
        async with httpx.AsyncClient(timeout=20) as client:
            while True:
                params: dict[str, Any] = {
                    "pageSize": 1000,
                    "personFields": "names,emailAddresses,organizations,relations,userDefined,metadata",
                    "requestSyncToken": "true",
                    "sortOrder": "LAST_MODIFIED_DESCENDING",
                }
                if sync_token:
                    params["syncToken"] = sync_token
                    params.pop("sortOrder", None)
                page_token: str | None = None
                restart = False
                while True:
                    if page_token:
                        params["pageToken"] = page_token
                    response = await client.get(CONTACTS_URL, params=params, headers=headers)
                    if response.status_code == 410 and sync_token and not retried_full_sync:
                        sync_token = None
                        account.sync_token = None
                        retried_full_sync = True
                        restart = True
                        break
                    self._raise_for_google_api(response, "Contacts")
                    payload = response.json()
                    for raw in payload.get("connections") or []:
                        resource_name = str(raw.get("resourceName") or "")
                        if not resource_name:
                            continue
                        metadata = raw.get("metadata") or {}
                        deleted = bool(metadata.get("deleted"))
                        contact = contacts.get(resource_name)
                        created = contact is None
                        if contact is None:
                            contact = GoogleContact(
                                user_id=account.user_id,
                                connected_account_id=account.id,
                                resource_name=resource_name,
                            )
                            self.session.add(contact)
                            contacts[resource_name] = contact
                        names = raw.get("names") or []
                        emails = self._contact_emails(raw.get("emailAddresses") or [])
                        organization = self._primary_organization(raw.get("organizations") or [])
                        contact.etag = str(raw.get("etag") or "")[:512]
                        contact.display_name = str((names[0] if names else {}).get("displayName") or "")[:300]
                        contact.emails = emails
                        contact.company = str(organization.get("name") or "")[:300]
                        contact.job_title = str(organization.get("title") or "")[:300]
                        contact.relationship_metadata = self._relationship_metadata(raw)
                        contact.provider_updated_at = self._google_datetime((metadata.get("sources") or [{}])[0].get("updateTime"))
                        contact.deleted = deleted
                        if deleted:
                            cancelled += 1
                        elif created:
                            synced += 1
                        else:
                            updated += 1
                    page_token = payload.get("nextPageToken")
                    if not page_token:
                        account.sync_token = payload.get("nextSyncToken") or account.sync_token
                        break
                if not restart:
                    break

        active = [contact for contact in contacts.values() if not contact.deleted]
        account.app_metadata = {
            **(account.app_metadata or {}),
            "contacts_count": len(active),
            "contacts_with_organization_count": sum(1 for contact in active if contact.company or contact.job_title),
            "contacts_with_relationship_count": sum(1 for contact in active if contact.relationship_metadata),
            "contact_name_by_email": {
                email.lower(): contact.display_name
                for contact in active
                if contact.display_name
                for email in contact.emails[:3]
            },
        }
        return WorkspaceSyncResult(synced=synced, updated=updated, cancelled=cancelled)

    async def _create_observations(self, account: ConnectedAppAccount) -> int:
        metadata = account.app_metadata or {}
        observations: list[str] = []
        if account.provider == "google_gmail":
            unread = int(metadata.get("unread_messages_estimate") or 0)
            mailbox = int(metadata.get("mailbox_messages_estimate") or 0)
            if unread >= 10:
                observations.append(f"Gmail signal: about {unread} unread messages may need triage.")
            if mailbox >= 50:
                observations.append(f"Gmail signal: high mailbox activity, about {mailbox} messages visible from metadata.")
        if account.provider == "google_drive":
            shared = int(metadata.get("shared_files_count") or 0)
            recent = int(metadata.get("recent_files_count") or 0)
            if recent >= 10:
                observations.append(f"Drive signal: {recent} recently modified files may reflect active work.")
            if shared >= 5:
                observations.append(f"Drive signal: {shared} recently active shared files may indicate collaboration load.")
        if account.provider == "google_tasks":
            overdue = int(metadata.get("overdue_tasks_count") or 0)
            active = int(metadata.get("active_tasks_count") or 0)
            completed = int(metadata.get("completed_tasks_count") or 0)
            if overdue:
                observations.append(f"Task evidence: {overdue} active task{'s are' if overdue != 1 else ' is'} overdue.")
            if active >= 5:
                observations.append(f"Task evidence: {active} active tasks are currently open.")
            if completed:
                observations.append(f"Task evidence: {completed} synced task{'s are' if completed != 1 else ' is'} completed.")
        if account.provider == "google_contacts":
            contacts = list(
                (
                    await self.session.execute(
                        select(GoogleContact).where(
                            GoogleContact.user_id == account.user_id,
                            GoogleContact.deleted.is_(False),
                        )
                    )
                ).scalars()
            )
            for contact in contacts:
                evidence = [value for value in (contact.job_title, contact.company) if value]
                relationships = list((contact.relationship_metadata or {}).get("relations") or [])
                if contact.display_name and (evidence or relationships):
                    detail = ", ".join([*relationships[:2], *evidence])
                    observations.append(f"Contact evidence: {contact.display_name} — {detail}.")

        existing = {
            item.content
            for item in (
                await self.session.execute(
                    select(LearningObservation).where(LearningObservation.user_id == account.user_id, LearningObservation.source == account.provider)
                )
            ).scalars()
        }
        created = 0
        for content in observations:
            if content in existing:
                continue
            self.session.add(LearningObservation(user_id=account.user_id, source=account.provider, content=content, status="observed"))
            created += 1
        await self.session.flush()
        return created

    async def _valid_access_token(self, account: ConnectedAppAccount, spec: GoogleServiceSpec) -> str:
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
            raise AppError(f"Google {spec.label} permission was revoked", status_code=409, code="permission_revoked", user_message=f"Google {spec.label} permission was revoked. Reconnect to resume sync.")
        if response.status_code >= 500:
            raise AppError("Google token refresh failed", status_code=503, code="google_unavailable", user_message="Google is unavailable right now. Try again later.")
        if response.status_code >= 400:
            raise AppError("Google token refresh failed", status_code=400, code="token_expired", user_message=f"Google {spec.label} authorization expired. Reconnect.")
        tokens = response.json()
        access = str(tokens["access_token"])
        account.encrypted_access_token = self._encrypt(access)
        account.access_token_expires_at = now + timedelta(seconds=int(tokens.get("expires_in") or 3600) - 60)
        return access

    async def _exchange_code(self, spec: GoogleServiceSpec, code: str) -> dict:
        redirect_uri = self._redirect_uri()
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    TOKEN_URL,
                    data={
                        "code": code,
                        "client_id": self.settings.google_connected_apps_client_id,
                        "client_secret": self.settings.google_connected_apps_client_secret,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code",
                    },
                )
        except Exception as exc:
            logger.exception(
                "Google Workspace OAuth token exchange request failed provider=%s token_endpoint=%s redirect_uri=%s client_id=%s scopes=%s",
                spec.provider,
                TOKEN_URL,
                redirect_uri,
                self._masked_client_id(),
                [spec.scope],
            )
            raise AppError(
                f"Google OAuth exchange request failed: {type(exc).__name__}: {exc}",
                status_code=400,
                code="oauth_exchange_failed",
                user_message=f"Google {spec.label} did not complete the connection. Try again.",
            ) from exc
        if response.status_code >= 400:
            response_body = self._safe_response_body(response, extra_secrets=(code,))
            logger.error(
                "Google Workspace OAuth token exchange failed provider=%s token_endpoint=%s redirect_uri=%s client_id=%s scopes=%s status=%s response_body=%s",
                spec.provider,
                TOKEN_URL,
                redirect_uri,
                self._masked_client_id(),
                [spec.scope],
                response.status_code,
                response_body,
            )
            raise AppError(
                f"Google OAuth exchange failed: status={response.status_code} response_body={response_body}",
                status_code=400,
                code="oauth_exchange_failed",
                user_message=f"Google {spec.label} did not complete the connection. Try again.",
            )
        return response.json()

    def _raise_for_google_api(self, response: httpx.Response, label: str) -> None:
        if response.status_code == 401:
            raise AppError(f"Google {label} permission was revoked", status_code=409, code="permission_revoked", user_message=f"Google {label} permission was revoked. Reconnect to resume sync.")
        if response.status_code == 403:
            detail = self._google_api_error_detail(response)
            raise AppError(
                f"Google {label} authorization failed: {detail}",
                status_code=403,
                code="google_permission_denied",
                user_message=f"Google {label} authorization failed: {detail}",
            )
        if response.status_code >= 500:
            raise AppError(f"Google {label} is unavailable", status_code=503, code="google_unavailable", user_message=f"Google {label} is unavailable right now. Try again later.")
        if response.status_code >= 400:
            detail = self._google_api_error_detail(response)
            raise AppError(f"Google {label} sync failed: {detail}", status_code=400, code="sync_failed", user_message=f"Google {label} sync failed: {detail}")

    async def _account(self, user_id: UUID, provider: str) -> ConnectedAppAccount | None:
        return await self.oauth.account(user_id, provider)

    async def _ensure_account(self, user_id: UUID, provider: str, scope: str) -> ConnectedAppAccount:
        return await self.oauth.ensure_account(user_id, provider, [scope])

    async def _required_account(self, user_id: UUID, provider: str) -> ConnectedAppAccount:
        return await self.oauth.required_account(user_id, provider)

    async def _mark_error(self, user_id: UUID, spec: GoogleServiceSpec, code: str, message: str) -> None:
        account = await self._ensure_account(user_id, spec.provider, spec.scope)
        await self._set_account_error(account, code, message)

    async def _set_account_error(self, account: ConnectedAppAccount, code: str, message: str, *, status: str = "error") -> None:
        account.status = status
        account.last_error_code = code
        account.last_error_message = message
        await self.session.flush()

    def _status_out(self, spec: GoogleServiceSpec, account: ConnectedAppAccount | None) -> dict:
        status = account.status if account else "not_connected"
        return {
            "provider": spec.provider,
            "status": status,
            "connected": status == "connected",
            "lastSyncedAt": account.last_synced_at if account else None,
            "lastErrorCode": account.last_error_code if account else None,
            "lastErrorMessage": account.last_error_message if account else None,
            "permissions": [spec.permission] if account and account.scopes else [],
            "scopes": account.scopes if account else [],
            "privacy": {
                "why": spec.why,
                "reads": spec.reads,
                "usage": spec.usage,
                "ignored": spec.ignored,
            },
        }

    def _encode_state(self, user_id: UUID, provider: str) -> str:
        payload = {
            "sub": str(user_id),
            "provider": provider,
            "nonce": secrets.token_urlsafe(12),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "type": "google_workspace_oauth_state",
        }
        return jwt.encode(payload, self.settings.jwt_secret_key, algorithm=self.settings.jwt_algorithm)

    def _decode_state(self, state: str) -> tuple[UUID, str]:
        try:
            payload = jwt.decode(state, self.settings.jwt_secret_key, algorithms=[self.settings.jwt_algorithm])
        except JWTError as exc:
            raise AppError("Invalid Google OAuth state", status_code=400, code="invalid_oauth_state") from exc
        if payload.get("type") != "google_workspace_oauth_state" or payload.get("provider") not in GOOGLE_SERVICES:
            raise AppError("Invalid Google OAuth state", status_code=400, code="invalid_oauth_state")
        return UUID(payload["sub"]), str(payload["provider"])

    def _decode_state_user(self, state: str | None) -> UUID | None:
        if not state:
            return None
        try:
            return self._decode_state(state)[0]
        except AppError:
            return None

    def _state_nonce(self, state: str) -> str:
        try:
            payload = jwt.decode(state, self.settings.jwt_secret_key, algorithms=[self.settings.jwt_algorithm])
            return str(payload["nonce"])
        except (JWTError, KeyError, TypeError) as exc:
            raise AppError("Invalid Google OAuth state", status_code=400, code="invalid_oauth_state") from exc

    async def _consume_state_nonce(self, user_id: UUID, nonce: str, provider: str) -> None:
        account = await self._account(user_id, provider)
        if not account or (account.app_metadata or {}).get("oauth_state_nonce") != nonce:
            raise AppError("Google OAuth state has already been used", status_code=400, code="invalid_oauth_state")
        metadata = dict(account.app_metadata or {})
        metadata.pop("oauth_state_nonce", None)
        account.app_metadata = metadata
        await self.session.flush()

    def _encrypt(self, value: str) -> str:
        return self.oauth.encrypt(value)

    def _decrypt(self, value: str) -> str:
        return self.oauth.decrypt(value)

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
                code="google_workspace_not_configured",
                user_message="Google Connected Apps are not configured for this environment yet.",
            )
        digest = hashlib.sha256(secret.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(digest))

    def _require_config(self, spec: GoogleServiceSpec) -> None:
        if (
            not self.settings.google_connected_apps_client_id
            or not self.settings.google_connected_apps_client_secret
            or not self.settings.google_connected_apps_redirect_uri
            or not self.settings.connected_app_token_secret
        ):
            raise AppError(f"Google {spec.label} is not configured", status_code=503, code="google_workspace_not_configured", user_message=f"Google {spec.label} is not configured for this Synzept environment yet.")

    def _redirect_uri(self) -> str:
        if self.settings.google_connected_apps_redirect_uri:
            return self.settings.google_connected_apps_redirect_uri
        if (self.settings.environment or "").lower() not in {"development", "dev", "local", "test", "testing"}:
            raise AppError("Google Connected Apps redirect URI is not configured", status_code=503, code="google_workspace_not_configured", user_message="Google Connected Apps are not configured for this environment yet.")
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

    def _google_api_error_detail(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except Exception:
            return self._sanitize_for_logs((response.text or f"HTTP {response.status_code}").strip()[:1000])
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            message = str(error.get("message") or "").strip()
            status = str(error.get("status") or "").strip()
            reasons = [
                str(item.get("reason"))
                for item in error.get("errors", [])
                if isinstance(item, dict) and item.get("reason")
            ]
            parts = [part for part in (status, message, ", ".join(reasons)) if part]
            if parts:
                return self._sanitize_for_logs(" - ".join(parts)[:1000])
        return self._sanitize_for_logs(str(payload)[:1000])

    def _gmail_label_counts(self, labels: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
        counts: dict[str, dict[str, int]] = {}
        for label in labels:
            if not isinstance(label, dict):
                continue
            label_id = str(label.get("id") or "").strip()
            if not label_id:
                continue
            counts[label_id] = {
                "messages_total": int(label.get("messagesTotal") or 0),
                "messages_unread": int(label.get("messagesUnread") or 0),
                "threads_total": int(label.get("threadsTotal") or 0),
                "threads_unread": int(label.get("threadsUnread") or 0),
            }
        return counts

    @staticmethod
    def _google_datetime(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _aware_datetime(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _contact_emails(items: list[dict[str, Any]]) -> list[str]:
        return list(dict.fromkeys(str(item.get("value") or "").strip().lower() for item in items if str(item.get("value") or "").strip()))[:10]

    @staticmethod
    def _primary_organization(items: list[dict[str, Any]]) -> dict[str, Any]:
        return next((item for item in items if (item.get("metadata") or {}).get("primary")), items[0] if items else {})

    @staticmethod
    def _relationship_metadata(person: dict[str, Any]) -> dict[str, Any]:
        relations = list(dict.fromkeys(str(item.get("type") or item.get("person") or "").strip() for item in person.get("relations") or [] if str(item.get("type") or item.get("person") or "").strip()))
        user_defined = {
            str(item.get("key") or "").strip(): str(item.get("value") or "").strip()
            for item in person.get("userDefined") or []
            if str(item.get("key") or "").strip() and str(item.get("value") or "").strip()
        }
        result: dict[str, Any] = {}
        if relations:
            result["relations"] = relations
        if user_defined:
            result["user_defined"] = user_defined
        return result

    def _sanitize_for_logs(self, value: str, *, extra_secrets: tuple[str, ...] = ()) -> str:
        sanitized = value
        for secret in (self.settings.google_connected_apps_client_secret, self.settings.connected_app_token_secret, self.settings.jwt_secret_key, *extra_secrets):
            if secret:
                sanitized = sanitized.replace(secret, "[redacted]")
        if self.settings.google_connected_apps_client_id:
            sanitized = sanitized.replace(self.settings.google_connected_apps_client_id, self._masked_client_id())
        return sanitized

    def _spec(self, provider: str) -> GoogleServiceSpec:
        try:
            return GOOGLE_SERVICES[provider]
        except KeyError as exc:
            raise AppError("Unsupported Google service", status_code=404, code="unsupported_google_service", user_message="That Google service is not available yet.") from exc

    @staticmethod
    def callback_provider(state: str | None) -> str | None:
        if not state:
            return None
        try:
            payload = jwt.get_unverified_claims(state)
        except Exception:
            return None
        provider = payload.get("provider")
        return str(provider) if provider in GOOGLE_SERVICES else None
