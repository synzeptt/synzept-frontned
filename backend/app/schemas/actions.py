from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import ORMModel


class ActionExecutionOut(ORMModel):
    id: UUID
    conversation_id: UUID | None
    project_id: UUID | None
    action_type: str
    title: str
    request: str
    status: str
    progress: int
    output: str | None
    error: str | None
    metadata: dict = Field(default_factory=dict, validation_alias="metadata_", serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime
