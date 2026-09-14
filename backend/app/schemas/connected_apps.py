from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ConnectedAppStatusOut(BaseModel):
    provider: str
    status: str
    connected: bool
    lastSyncedAt: datetime | None
    lastErrorCode: str | None
    lastErrorMessage: str | None
    permissions: list[str]
    scopes: list[str]
    privacy: dict[str, str]


class ConnectUrlOut(BaseModel):
    authorizationUrl: str


class CalendarSyncOut(BaseModel):
    synced: int
    updated: int
    cancelled: int
    observations: int
    status: str


class CalendarContextOut(BaseModel):
    today: list[dict[str, Any]]
    tomorrow: list[dict[str, Any]]
    meetingLoadMinutes: int
    freeBlocks: list[dict[str, Any]]
    conflicts: list[str]
    recommendation: str


class CalendarWeeklyContextOut(BaseModel):
    events: int
    meetingLoadMinutes: int
    recurringEvents: int
    heavyMeetingDays: list[str]
    summary: str
