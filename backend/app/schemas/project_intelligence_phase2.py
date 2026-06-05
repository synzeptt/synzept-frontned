from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ProjectStatus = Literal["active", "paused", "completed", "archived"]
OpenLoopStatus = Literal["open", "completed", "archived"]
DecisionStatus = Literal["pending", "decided"]


class ProjectCreatePhase2(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    currentFocus: str = Field(default="", max_length=4000)
    recommendedNextStep: str = Field(default="", max_length=4000)
    status: ProjectStatus = "active"


class ProjectUpdatePhase2(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    currentFocus: str | None = Field(default=None, max_length=4000)
    recommendedNextStep: str | None = Field(default=None, max_length=4000)
    status: ProjectStatus | None = None


class ProjectOutPhase2(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    userId: UUID
    name: str
    description: str
    currentFocus: str
    recommendedNextStep: str
    status: ProjectStatus
    createdAt: datetime
    updatedAt: datetime


class OpenLoopCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=4000)
    status: OpenLoopStatus = "open"


class OpenLoopUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    status: OpenLoopStatus | None = None


class OpenLoopOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    projectId: UUID
    title: str
    description: str
    status: OpenLoopStatus
    createdAt: datetime
    updatedAt: datetime


class DecisionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=4000)
    status: DecisionStatus = "pending"


class DecisionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    status: DecisionStatus | None = None


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    projectId: UUID
    title: str
    description: str
    status: DecisionStatus
    createdAt: datetime
    updatedAt: datetime
