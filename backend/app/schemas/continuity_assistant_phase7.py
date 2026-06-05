from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ContinuityAssistantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None
    userId: UUID
    contextSnapshotId: UUID | None
    whatChanged: list[dict[str, Any]]
    whatMatters: list[dict[str, Any]]
    openLoops: list[dict[str, Any]]
    recentProgress: list[dict[str, Any]]
    recommendedNextStep: dict[str, Any]
    createdAt: datetime | None
    updatedAt: datetime | None
