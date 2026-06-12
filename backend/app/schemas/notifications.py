from datetime import datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


NotificationType = Literal[
    "daily_brief",
    "open_loop",
    "project_attention",
    "return_to_work",
]
NotificationChannel = Literal["in_app", "email", "push"]
NotificationFrequency = Literal["daily", "weekdays", "important_only", "off"]


class NotificationSettingsOut(BaseModel):
    enabled: bool = True
    dailyBrief: bool = True
    openLoops: bool = True
    projectAttention: bool = True
    returnToWork: bool = True
    email: bool = False
    push: bool = False
    frequency: NotificationFrequency = "daily"
    morningTime: str = "09:00"


class NotificationSettingsUpdate(BaseModel):
    enabled: bool | None = None
    dailyBrief: bool | None = None
    openLoops: bool | None = None
    projectAttention: bool | None = None
    returnToWork: bool | None = None
    email: bool | None = None
    push: bool | None = None
    frequency: NotificationFrequency | None = None
    morningTime: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")


class NotificationOut(BaseModel):
    id: UUID
    notificationType: str
    channel: str
    title: str
    message: str
    status: str
    priority: str
    scheduledFor: datetime | None = None
    sentAt: datetime | None = None
    readAt: datetime | None = None
    metadata: dict = Field(default_factory=dict)
    createdAt: datetime
    updatedAt: datetime


class NotificationDigestOut(BaseModel):
    settings: NotificationSettingsOut
    notifications: list[NotificationOut] = Field(default_factory=list)
    generated: int = 0
    unread: int = 0
