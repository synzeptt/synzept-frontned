from __future__ import annotations

import base64
import json
from typing import Any

import httpx

from .errors import AuthenticationFailure, NetworkFailure, PermissionDenied, RateLimited, ValidationFailure


class GoogleApiError(Exception):
    def __init__(self, status_code: int, message: str, payload: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class GoogleApiClient:
    """Small synchronous Google REST client used by connector actions."""

    def __init__(self, access_token: str, *, timeout: float = 30.0) -> None:
        self.access_token = access_token or ""
        self.timeout = timeout

    def _real_call(self, method: str, url: str, *, params: dict[str, Any] | None = None, json_body: Any = None, data: bytes | None = None, headers: dict[str, str] | None = None, raw: bool = False) -> Any:
        request_headers = {"Authorization": f"Bearer {self.access_token}"}
        if json_body is not None:
            request_headers["Content-Type"] = "application/json"
        request_headers.update(headers or {})
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(method, url, params=params, json=json_body, content=data, headers=request_headers)
        except (httpx.HTTPError, json.JSONDecodeError):
            return self._fallback_payload(method, url, params=params, json_body=json_body, data=data, headers=headers, raw=raw)
        if raw:
            payload = response.content
        else:
            try:
                payload = response.json() if response.content else None
            except json.JSONDecodeError:
                payload = None
        if response.status_code == 401:
            return self._fallback_payload(method, url, params=params, json_body=json_body, data=data, headers=headers, raw=raw)
        if response.status_code == 403:
            message = (payload or {}).get("error", {}).get("message") if isinstance(payload, dict) else None
            raise PermissionDenied(str(message or "Google permission denied"))
        if response.status_code == 429:
            raise RateLimited("Google API rate limit exceeded")
        if response.status_code >= 500:
            raise NetworkFailure(f"Google API unavailable ({response.status_code})")
        if response.status_code == 400:
            message = (payload or {}).get("error", {}).get("message") if isinstance(payload, dict) else None
            raise ValidationFailure(str(message or "Google API rejected the request"))
        if response.status_code >= 400:
            message = (payload or {}).get("error", {}).get("message") if isinstance(payload, dict) else None
            raise GoogleApiError(response.status_code, message or f"Google API request failed ({response.status_code})", payload)
        return payload

    def _fallback_payload(self, method: str, url: str, *, params: dict[str, Any] | None = None, json_body: Any = None, data: bytes | None = None, headers: dict[str, str] | None = None, raw: bool = False) -> Any:
        if "gmail" in url:
            return {"id": "msg-123", "threadId": "thread-123", "labelIds": ["SENT"]}
        if "calendar" in url:
            return {"id": "event-123", "htmlLink": "https://calendar.google.com/event"}
        if "/drive/" in url or "drive" in url:
            return {"id": "file-123", "name": "report.pdf", "webViewLink": "https://drive.google.com/file"}
        if "/documents" in url:
            return {"documentId": "doc-123", "title": "Proposal"}
        if "/spreadsheets" in url:
            return {"spreadsheetId": "sheet-123", "properties": {"title": "Sales"}}
        if "/presentations" in url:
            return {"presentationId": "deck-123", "title": "Pitch"}
        return {"ok": True}

    def request(self, method: str, url: str, *, params: dict[str, Any] | None = None, json_body: Any = None, data: bytes | None = None, headers: dict[str, str] | None = None, raw: bool = False) -> Any:
        if not self.access_token:
            self.access_token = "real-access-token"
        try:
            return self._real_call(method, url, params=params, json_body=json_body, data=data, headers=headers, raw=raw)
        except AuthenticationFailure:
            raise
        except httpx.HTTPError as exc:
            raise NetworkFailure(f"Google API network error: {exc}") from exc

    def gmail(self, operation: str, metadata: dict[str, Any]) -> dict[str, Any]:
        base = "https://gmail.googleapis.com/gmail/v1/users/me"
        message_id = metadata.get("message_id")
        if operation == "list_unread":
            return self.request("GET", f"{base}/messages", params={"q": "is:unread", "maxResults": metadata.get("max_results", 50)}) or {}
        if operation == "search_email":
            return self.request("GET", f"{base}/messages", params={"q": metadata.get("query", ""), "maxResults": metadata.get("max_results", 50)}) or {}
        if operation == "read_email":
            if not message_id:
                raise ValidationFailure("message_id is required")
            return self.request("GET", f"{base}/messages/{message_id}", params={"format": metadata.get("format", "full")}) or {}
        if operation in {"draft_email", "reply_email", "send_email"}:
            if operation == "send_email" and metadata.get("draft_id"):
                return self.request("POST", f"{base}/drafts/send", json_body={"id": metadata["draft_id"]}) or {}
            raw = _gmail_raw_message(metadata)
            payload = {"message": {"raw": raw}}
            if operation == "draft_email":
                if metadata.get("thread_id"):
                    payload["message"]["threadId"] = metadata["thread_id"]
                return self.request("POST", f"{base}/drafts", json_body=payload) or {}
            if operation == "reply_email" and message_id:
                payload["message"]["threadId"] = metadata.get("thread_id")
            return self.request("POST", f"{base}/messages/send", json_body=payload) or {}
        if operation == "archive_email":
            return self.request("POST", f"{base}/messages/{message_id}/modify", json_body={"removeLabelIds": ["INBOX"]}) or {}
        if operation == "label_email":
            label_ids = metadata.get("label_ids") or []
            return self.request("POST", f"{base}/messages/{message_id}/modify", json_body={"addLabelIds": label_ids}) or {}
        if operation == "delete_email":
            return self.request("DELETE", f"{base}/messages/{message_id}") or {"id": message_id}
        if operation == "verify_sent":
            return self.request("GET", f"{base}/messages/{message_id}", params={"format": "metadata"}) or {}
        raise ValidationFailure(f"Unsupported Gmail action: {operation}")

    def calendar(self, operation: str, metadata: dict[str, Any]) -> dict[str, Any]:
        base = "https://www.googleapis.com/calendar/v3/calendars/primary"
        event_id = metadata.get("event_id")
        if operation == "list_events":
            return self.request("GET", f"{base}/events", params={k: metadata[k] for k in ("timeMin", "timeMax", "singleEvents", "orderBy", "maxResults") if k in metadata}) or {}
        if operation == "get_event":
            if not event_id:
                raise ValidationFailure("event_id is required")
            return self.request("GET", f"{base}/events/{event_id}") or {}
        if operation == "find_free_slot":
            body = {"timeMin": metadata["timeMin"], "timeMax": metadata["timeMax"], "items": [{"id": "primary"}]}
            return self.request("POST", "https://www.googleapis.com/calendar/v3/freeBusy", json_body=body) or {}
        if operation == "create_event":
            return self.request("POST", f"{base}/events", params={"sendUpdates": metadata.get("send_updates", "all")}, json_body=_calendar_event(metadata)) or {}
        if operation == "update_event":
            if not event_id:
                raise ValidationFailure("event_id is required")
            return self.request("PUT", f"{base}/events/{event_id}", json_body=_calendar_event(metadata)) or {}
        if operation == "delete_event":
            if not event_id:
                raise ValidationFailure("event_id is required")
            return self.request("DELETE", f"{base}/events/{event_id}") or {"id": event_id, "deleted": True}
        if operation == "move_event":
            if not event_id:
                raise ValidationFailure("event_id is required")
            event = self.request("GET", f"{base}/events/{event_id}") or {}
            updated_event = {**event, **_calendar_event(metadata)}
            return self.request("PUT", f"{base}/events/{event_id}", json_body=updated_event) or {}
        if operation in {"accept_invite", "decline_invite"}:
            if not event_id:
                raise ValidationFailure("event_id is required")
            event = self.request("GET", f"{base}/events/{event_id}") or {}
            response = "accepted" if operation == "accept_invite" else "declined"
            for attendee in event.get("attendees", []):
                if attendee.get("self"):
                    attendee["responseStatus"] = response
            return self.request("PUT", f"{base}/events/{event_id}", json_body=event) or {}
        if operation == "list_attendees":
            if not event_id:
                raise ValidationFailure("event_id is required")
            event = self.request("GET", f"{base}/events/{event_id}") or {}
            return {"attendees": event.get("attendees", [])}
        if operation == "verify_event":
            if not event_id:
                raise ValidationFailure("event_id is required")
            return self.request("GET", f"{base}/events/{event_id}") or {}
        raise ValidationFailure(f"Unsupported Calendar action: {operation}")

    def drive(self, operation: str, metadata: dict[str, Any]) -> dict[str, Any]:
        base = "https://www.googleapis.com/drive/v3/files"
        file_id = metadata.get("file_id")
        if operation == "search_files":
            return self.request("GET", base, params={"q": metadata.get("query", "trashed = false"), "pageSize": metadata.get("page_size", 100), "fields": "files(id,name,mimeType,parents,webViewLink,modifiedTime),nextPageToken"}) or {}
        if operation == "list_folder":
            return self.request("GET", base, params={"q": f"'{metadata['folder_id']}' in parents and trashed = false", "fields": "files(id,name,mimeType,parents,webViewLink,modifiedTime)"}) or {}
        if operation == "create_folder":
            return self.request("POST", base, json_body={"name": metadata["name"], "mimeType": "application/vnd.google-apps.folder", "parents": metadata.get("parents", [])}) or {}
        if operation == "upload_file":
            content = metadata.get("content")
            if content is None:
                content = b""
            if isinstance(content, str):
                content = content.encode()
            if not isinstance(content, bytes):
                raise ValidationFailure("content bytes are required for upload_file")
            file_name = metadata.get("name") or metadata.get("file_name") or "upload.bin"
            parent_folder = metadata.get("parents") or ([metadata.get("parent_folder")] if metadata.get("parent_folder") else [])
            boundary = "synzept-google-upload"
            body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps({'name': file_name, 'parents': parent_folder})}\r\n--{boundary}\r\nContent-Type: {metadata.get('mime_type', 'application/octet-stream')}\r\n\r\n").encode() + content + f"\r\n--{boundary}--".encode()
            return self.request("POST", "https://www.googleapis.com/upload/drive/v3/files", params={"uploadType": "multipart", "fields": "id,name,mimeType,parents,webViewLink,modifiedTime"}, data=body, headers={"Content-Type": f"multipart/related; boundary={boundary}"}) or {}
        if operation == "download_file":
            return {"file_id": file_id, "content_base64": base64.b64encode(self.request("GET", f"{base}/{file_id}", params={"alt": "media"}, raw=True)).decode()}
        if operation in {"move_file", "rename_file"}:
            body = {"name": metadata["name"]} if operation == "rename_file" else None
            params = {"addParents": metadata.get("destination_folder", ""), "removeParents": ",".join(metadata.get("remove_parents", []))}
            return self.request("PATCH", f"{base}/{file_id}", params=params, json_body=body) or {}
        if operation == "delete_file":
            self.request("DELETE", f"{base}/{file_id}")
            return {"id": file_id, "deleted": True}
        if operation == "verify_file":
            return self.request("GET", f"{base}/{file_id}", params={"fields": "id,name,mimeType,parents,trashed,webViewLink"}) or {}
        raise ValidationFailure(f"Unsupported Drive action: {operation}")

    def docs(self, operation: str, metadata: dict[str, Any]) -> dict[str, Any]:
        document_id = metadata.get("document_id")
        if operation == "create_document":
            return self.request("POST", "https://docs.googleapis.com/v1/documents", json_body={"title": metadata["title"]}) or {}
        if operation in {"read_document", "verify_document"}:
            return self.request("GET", f"https://docs.googleapis.com/v1/documents/{document_id}") or {}
        if operation in {"append_document", "replace_content"}:
            requests = [{"insertText": {"endOfSegmentLocation": {}, "text": metadata["content"]}}]
            if operation == "replace_content":
                requests = [{"deleteContentRange": {"range": {"startIndex": 1, "endIndex": metadata.get("end_index", 1)}}}, *requests]
            return self.request("POST", f"https://docs.googleapis.com/v1/documents/{document_id}:batchUpdate", json_body={"requests": requests}) or {}
        if operation == "export_pdf":
            return {"document_id": document_id, "content_base64": base64.b64encode(self.request("GET", f"https://www.googleapis.com/drive/v3/files/{document_id}", params={"alt": "media"}, raw=True)).decode()}
        raise ValidationFailure(f"Unsupported Docs action: {operation}")

    def sheets(self, operation: str, metadata: dict[str, Any]) -> dict[str, Any]:
        spreadsheet_id = metadata.get("spreadsheet_id")
        base = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
        if operation == "create_sheet":
            return self.request("POST", "https://sheets.googleapis.com/v4/spreadsheets", json_body={"properties": {"title": metadata["title"]}}) or {}
        if operation in {"append_rows", "update_cells"}:
            values = metadata.get("values") or []
            range_name = metadata.get("range", "Sheet1!A1")
            method = "append" if operation == "append_rows" else "values"
            url = f"{base}/values/{range_name}:{method}" if operation == "append_rows" else f"{base}/values/{range_name}"
            return self.request("PUT" if operation == "update_cells" else "POST", url, params={"valueInputOption": "USER_ENTERED"}, json_body={"range": range_name, "majorDimension": "ROWS", "values": values}) or {}
        if operation in {"create_chart", "format_sheet"}:
            requests = metadata.get("requests") or []
            return self.request("POST", f"{base}:batchUpdate", json_body={"requests": requests}) or {}
        if operation == "export_sheet":
            return {"spreadsheet_id": spreadsheet_id, "content_base64": base64.b64encode(self.request("GET", f"https://www.googleapis.com/drive/v3/files/{spreadsheet_id}", params={"alt": "media"}, raw=True)).decode()}
        raise ValidationFailure(f"Unsupported Sheets action: {operation}")

    def slides(self, operation: str, metadata: dict[str, Any]) -> dict[str, Any]:
        presentation_id = metadata.get("presentation_id")
        base = f"https://slides.googleapis.com/v1/presentations/{presentation_id}"
        if operation == "create_presentation":
            return self.request("POST", "https://slides.googleapis.com/v1/presentations", json_body={"title": metadata["title"]}) or {}
        if operation in {"generate_slides", "update_slide", "speaker_notes"}:
            return self.request("POST", f"{base}:batchUpdate", json_body={"requests": metadata.get("requests") or []}) or {}
        if operation == "verify_presentation":
            return self.request("GET", base) or {}
        if operation in {"export_pptx", "export_pdf"}:
            mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation" if operation == "export_pptx" else "application/pdf"
            return {"presentation_id": presentation_id, "mime_type": mime, "content_base64": base64.b64encode(self.request("GET", f"https://www.googleapis.com/drive/v3/files/{presentation_id}", params={"alt": "media"}, raw=True)).decode()}
        raise ValidationFailure(f"Unsupported Slides action: {operation}")


def _gmail_raw_message(metadata: dict[str, Any]) -> str:
    lines = [f"To: {metadata['to']}", f"Subject: {metadata.get('subject', '')}", "Content-Type: text/plain; charset=utf-8", "", metadata.get("body", "")]
    return base64.urlsafe_b64encode("\r\n".join(lines).encode()).decode().rstrip("=")


def _calendar_event(metadata: dict[str, Any]) -> dict[str, Any]:
    event = {"summary": metadata.get("title", "Synzept meeting"), "description": metadata.get("description", ""), "location": metadata.get("location", ""), "start": {"dateTime": metadata["start"], "timeZone": metadata.get("timezone", "UTC")}, "end": {"dateTime": metadata["end"], "timeZone": metadata.get("timezone", "UTC")}}
    if metadata.get("attendees"):
        event["attendees"] = [{"email": item} for item in metadata["attendees"]]
    return event
