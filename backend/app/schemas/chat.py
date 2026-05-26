from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.reliability import sanitize_user_input

from app.schemas.base import ORMModel, TimestampedSchema


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=16000)
    conversation_id: UUID | None = None
    project_id: UUID | None = None
    provider: str | None = Field(default=None, pattern="^(openai|anthropic)$")
    model: str | None = Field(default=None, max_length=120)
    temperature: float = Field(default=0.3, ge=0, le=2)
    max_tokens: int = Field(default=1200, ge=1, le=8000)

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        cleaned = sanitize_user_input(value)
        if not cleaned:
            raise ValueError("Message cannot be empty")
        return cleaned


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    project_id: UUID | None = None
    conversation_type: str = Field(default="general", max_length=50)
    summary: str | None = None


class ConversationRename(BaseModel):
    title: str = Field(min_length=1, max_length=300)


class ConversationSummaryUpdate(BaseModel):
    summary: str | None = None


class MessageCreate(BaseModel):
    role: str = Field(pattern="^(user|assistant|system)$")
    content: str = Field(min_length=1, max_length=64000)
    token_count: int | None = Field(default=None, ge=0)
    provider_name: str | None = Field(default=None, max_length=50)
    model_name: str | None = Field(default=None, max_length=120)
    metadata: dict = Field(default_factory=dict)


class ConversationOut(TimestampedSchema):
    id: UUID
    title: str | None
    project_id: UUID | None
    summary: str | None
    conversation_type: str
    archived_at: datetime | None


class MessageOut(TimestampedSchema):
    id: UUID
    role: str
    content: str
    conversation_id: UUID
    token_count: int | None
    provider_name: str | None
    model_name: str | None
    metadata: dict = Field(default_factory=dict, validation_alias="metadata_", serialization_alias="metadata")

    model_config = ORMModel.model_config | {"populate_by_name": True}


class StreamPreparedResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    status: str = "ready"


class ActionSuggestionOut(BaseModel):
    type: str
    label: str
    description: str
    requires_confirmation: bool = True


class ChatResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    reply: str
    intent: str | None = None
    suggestions: list[ActionSuggestionOut] = Field(default_factory=list)
