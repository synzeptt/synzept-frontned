"""Read-only Google Calendar capability for the agent tool registry."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.agent.models import ToolDefinition, ToolInputSchema, ToolOutputSchema
from app.agent.tool import BaseTool
from app.database.session import SessionLocal
from app.models.connected_app import ConnectedAppAccount
from app.services.connected_apps.google_calendar_service import GoogleCalendarService


class CalendarListUpcomingEventsTool(BaseTool):
    def __init__(self, session_factory=SessionLocal) -> None:
        super().__init__()
        self.session_factory = session_factory

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="calendar.list_upcoming_events",
            description="Read the user's connected Google Calendar events in a bounded time window.",
            input_schema=ToolInputSchema(
                properties={
                    "start_time": {"type": "string", "description": "ISO-8601 start time or today/tomorrow"},
                    "end_time": {"type": "string", "description": "ISO-8601 end time or today/tomorrow"},
                    "query": {"type": "string", "description": "Optional title or description search"},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
                },
                required=["start_time", "end_time"],
            ),
            output_schema=ToolOutputSchema(properties={"success": {"type": "boolean"}, "events": {"type": "array"}, "count": {"type": "integer"}, "error": {"type": "string"}}),
            category="calendar",
        )

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("Calendar access requires trusted execution context")

    async def execute_with_context(self, step_id: str, parameters: dict[str, Any], execution_context: dict[str, Any] | None = None):
        try:
            user_id = _trusted_user_id(execution_context)
            if not user_id:
                return self._failure(step_id, "Calendar access is unavailable for this execution.")

            async with self.session_factory() as session:
                connected = await self._has_connected_calendar_account(session, user_id)
                if not connected:
                    return self._failure(step_id, "Google Calendar is not connected for this user.")

                start = _parse_time(parameters.get("start_time"))
                end = _parse_time(parameters.get("end_time"))
                if not start or not end or end <= start:
                    return self._failure(step_id, "Calendar time range is invalid.")
                if end - start > timedelta(days=31):
                    return self._failure(step_id, "Calendar time range cannot exceed 31 days.")
                max_results = min(max(int(parameters.get("max_results", 10)), 1), 20)
                query = str(parameters.get("query") or "").strip()[:160].casefold()
                service = GoogleCalendarService(session)
                await service.sync(user_id)
                events = await service.list_upcoming_events(user_id=user_id, start=start, end=end, query=query, max_results=max_results)
            return self._success(step_id, events)
        except Exception as exc:
            return self._failure(step_id, _calendar_error(exc))

    @staticmethod
    async def _has_connected_calendar_account(session, user_id: UUID) -> bool:
        execute = getattr(session, "execute", None)
        if execute is None:
            return True
        try:
            result = await execute(
                select(ConnectedAppAccount.id).where(
                    ConnectedAppAccount.user_id == user_id,
                    ConnectedAppAccount.provider == "google_calendar",
                    ConnectedAppAccount.status == "connected",
                ).limit(1)
            )
        except Exception:
            return True
        return result.scalar_one_or_none() is not None

    @staticmethod
    def _success(step_id: str, events: list[dict[str, Any]]):
        return _result(step_id, events)

    @staticmethod
    def _failure(step_id: str, message: str):
        from app.agent.models import ToolExecutionResult
        return ToolExecutionResult(tool_name="calendar.list_upcoming_events", step_id=step_id, success=False, error=message)


def _result(step_id: str, events: list[dict[str, Any]]):
    from app.agent.models import ToolExecutionResult
    return ToolExecutionResult(tool_name="calendar.list_upcoming_events", step_id=step_id, success=True, output={"success": True, "events": events, "count": len(events)})


def _trusted_user_id(context: dict[str, Any] | None) -> UUID | None:
    value = (context or {}).get("user_id")
    try:
        return UUID(str(value)) if value else None
    except (TypeError, ValueError):
        return None


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    now = datetime.now(timezone.utc)
    lowered = value.strip().casefold()
    if lowered in {"today", "tomorrow"}:
        day = now.date() + timedelta(days=1 if lowered == "tomorrow" else 0)
        return datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _calendar_error(exc: Exception) -> str:
    name = exc.__class__.__name__
    if name in {"NotFoundError", "PermissionDenied"}:
        return "Google Calendar is not connected or does not have the required permission."
    return "Google Calendar could not be read right now. Reconnect Calendar or try again later."