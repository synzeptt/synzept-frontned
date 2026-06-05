from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ContextSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None
    userId: UUID
    currentFocus: dict[str, Any]
    activeThemes: list[dict[str, Any]]
    openLoops: list[dict[str, Any]]
    importantContext: list[dict[str, Any]]
    recommendedNextStep: dict[str, Any]
    createdAt: datetime | None
    updatedAt: datetime | None
