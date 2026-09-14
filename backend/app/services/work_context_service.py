from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connected_app import ConnectedAppAccount
from app.models.task import Task


class WorkContextService:
    """Resolves connected-app and workspace context that can enrich Work execution."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def build_context(self, *, user_id: UUID, request: str) -> list[dict[str, Any]]:
        context: list[dict[str, Any]] = []
        connected = await self._connected_accounts(user_id)

        if self._should_include_calendar(request, connected):
            context.append(self._calendar_context(connected))

        if self._should_include_gmail(request):
            account = next((item for item in connected if item.provider == "google_gmail" and item.status == "connected"), None)
            context.append({
                "kind": "connected_source",
                "title": "Gmail",
                "detail": "Gmail is connected and available for this request." if account else "Connect Gmail before asking Synzept to review or send email.",
                "source": "connected_app" if account else "connect",
            })

        related_work = await self._related_work(user_id, request)
        if related_work:
            context.append(related_work)

        if not context:
            context.append({"kind": "generic", "title": "Context", "detail": "No connected context is available yet.", "source": "none"})
        return context

    async def _connected_accounts(self, user_id: UUID) -> list[ConnectedAppAccount]:
        result = await self.session.execute(select(ConnectedAppAccount).where(ConnectedAppAccount.user_id == user_id))
        return list(result.scalars().all())

    async def _related_work(self, user_id: UUID, request: str) -> dict[str, Any] | None:
        if not any(keyword in request.casefold() for keyword in ["meeting", "brief", "review", "client", "prepare", "tomorrow"]):
            return None
        result = await self.session.execute(select(Task).where(Task.user_id == user_id).order_by(Task.updated_at.desc()).limit(3))
        tasks = list(result.scalars().all())
        if not tasks:
            return None
        return {
            "kind": "related_work",
            "title": "Related work",
            "detail": "Recent tasks can help Synzept keep the new work aligned with the wider plan.",
            "items": [
                {"id": str(task.id), "title": task.title, "detail": task.description or "No additional detail"}
                for task in tasks[:3]
            ],
            "source": "workspace",
        }

    def _calendar_context(self, accounts: list[ConnectedAppAccount]) -> dict[str, Any]:
        account = next((item for item in accounts if item.provider == "google_calendar" and item.status == "connected"), None)
        if not account:
            return {"kind": "calendar", "title": "Calendar", "detail": "Connect Google Calendar to see meetings and scheduling context.", "source": "connect"}
        metadata = dict(account.app_metadata or {})
        meetings = metadata.get("upcoming_meetings") or []
        if not isinstance(meetings, list) or not meetings:
            return {"kind": "calendar", "title": "Calendar", "detail": "Calendar is connected, but no upcoming meetings were surfaced yet.", "source": "connected_app"}
        return {
            "kind": "calendar",
            "title": "Calendar context",
            "detail": "Upcoming meetings are available to ground the request in your real schedule.",
            "items": [
                {"title": str(item.get("title") or "Untitled meeting"), "detail": self._format_meeting(item)}
                for item in meetings[:3]
            ],
            "source": "connected_app",
        }

    def _should_include_calendar(self, request: str, accounts: list[ConnectedAppAccount]) -> bool:
        lowered = request.casefold()
        return any(keyword in lowered for keyword in ["meeting", "calendar", "brief", "prepare", "tomorrow", "today", "review", "client", "schedule"])

    @staticmethod
    def _should_include_gmail(request: str) -> bool:
        lowered = request.casefold()
        return any(keyword in lowered for keyword in ["email", "gmail", "inbox", "reply", "replies"])

    @staticmethod
    def _format_meeting(item: dict[str, Any]) -> str:
        start = item.get("startAt") or ""
        end = item.get("endAt") or ""
        if start and end:
            return f"{start} to {end}"
        return "Meeting details pending"
