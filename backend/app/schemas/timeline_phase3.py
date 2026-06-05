from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


TimelineEventType = Literal["milestone", "decision", "learning", "achievement", "progress"]


class TimelineEventCreate(BaseModel):
    eventType: TimelineEventType
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=4000)
    eventDate: date
    importance: float = Field(default=0.5, ge=0, le=1)
    projectId: UUID | None = None


class TimelineEventUpdate(BaseModel):
    eventType: TimelineEventType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    eventDate: date | None = None
    importance: float | None = Field(default=None, ge=0, le=1)
    projectId: UUID | None = None


class TimelineEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    userId: UUID
    projectId: UUID | None = None
    eventType: TimelineEventType
    title: str
    description: str
    eventDate: date
    importance: float
    createdAt: datetime
    updatedAt: datetime
