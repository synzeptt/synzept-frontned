from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DailyBriefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None
    userId: UUID
    contextSnapshotId: UUID | None
    briefDate: date
    whatMattersToday: list[dict[str, Any]]
    whatChanged: list[dict[str, Any]]
    openLoops: list[dict[str, Any]]
    recommendedNextStep: dict[str, Any]
    focusForToday: dict[str, Any]
    currentMission: dict[str, Any]
    currentFocus: dict[str, Any]
    recentProgress: list[dict[str, Any]]
    recentDecisions: list[dict[str, Any]]
    upcomingPriorities: list[dict[str, Any]]
    projectsNeedingAttention: list[dict[str, Any]]
    contextToRemember: list[dict[str, Any]]
    createdAt: datetime | None
    updatedAt: datetime | None
