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
    openLoops: list[dict[str, Any]]
    recommendedNextStep: dict[str, Any]
    recentProgress: list[dict[str, Any]]
    contextToRemember: list[dict[str, Any]]
    createdAt: datetime | None
    updatedAt: datetime | None
