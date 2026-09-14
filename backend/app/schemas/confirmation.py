from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ConfirmationOut(BaseModel):
    id: UUID
    user_id: UUID
    requested_action: str
    tool_name: str
    tool_arguments: dict = Field(default_factory=dict)
    human_readable_summary: str
    risk_level: str
    status: str
    created_at: datetime
    expires_at: datetime


class ConfirmationDecisionResponse(BaseModel):
    ok: bool
    confirmation_id: UUID
    status: str
    message: str
