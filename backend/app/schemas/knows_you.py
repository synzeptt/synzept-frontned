from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserUnderstandingBody(BaseModel):
    personal: dict[str, Any] = Field(default_factory=dict)
    professional: dict[str, Any] = Field(default_factory=dict)
    goals: dict[str, Any] = Field(default_factory=dict)
    preferences: dict[str, Any] = Field(default_factory=dict)
    learning: dict[str, Any] = Field(default_factory=dict)
    currentFocus: dict[str, Any] = Field(default_factory=dict)


class UserUnderstandingProfileOut(UserUnderstandingBody):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    userId: UUID
    createdAt: datetime
    updatedAt: datetime


class LearningSuggestionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=4000)


class LearningSuggestionEdit(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, min_length=1, max_length=4000)


class LearningSuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    userId: UUID
    title: str
    description: str
    status: Literal["pending", "accepted", "ignored"]
    createdAt: datetime
    updatedAt: datetime
