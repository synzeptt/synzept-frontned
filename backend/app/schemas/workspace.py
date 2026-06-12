from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.goal import GoalOut, NextActionOut
from app.schemas.memory import MemoryOut
from app.schemas.note import NoteCreate, NoteOut, NoteUpdate
from app.schemas.task import TaskOut


class WorkspaceProjectOut(BaseModel):
    id: UUID
    title: str
    description: str
    status: str
    goals: list[GoalOut] = Field(default_factory=list)
    tasks: list[TaskOut] = Field(default_factory=list)
    notes: list[NoteOut] = Field(default_factory=list)
    progress: float = 0.0


class WorkspaceProgressOut(BaseModel):
    goal_completion: float = 0.0
    project_completion: float = 0.0
    task_completion: float = 0.0
    weekly_productivity_trend: float = 0.0


class WorkspaceInsightOut(BaseModel):
    type: str
    title: str
    detail: str
    severity: str = "info"
    project_id: UUID | None = None
    goal_id: UUID | None = None
    task_id: UUID | None = None


class WorkspaceActivityOut(BaseModel):
    id: UUID
    action: str
    title: str
    detail: str
    project_id: UUID | None = None
    goal_id: UUID | None = None
    task_id: UUID | None = None
    note_id: UUID | None = None
    created_at: datetime


class WorkspaceOut(BaseModel):
    projects: list[WorkspaceProjectOut] = Field(default_factory=list)
    goals: list[GoalOut] = Field(default_factory=list)
    tasks: list[TaskOut] = Field(default_factory=list)
    notes: list[NoteOut] = Field(default_factory=list)
    memories: list[MemoryOut] = Field(default_factory=list)
    progress: WorkspaceProgressOut = Field(default_factory=WorkspaceProgressOut)
    insights: list[WorkspaceInsightOut] = Field(default_factory=list)
    recommendations: list[NextActionOut] = Field(default_factory=list)
    timeline: list[WorkspaceActivityOut] = Field(default_factory=list)


class WorkspaceSearchResult(BaseModel):
    type: str
    id: UUID
    title: str
    detail: str
    project_id: UUID | None = None
    goal_id: UUID | None = None


class WorkspaceSearchOut(BaseModel):
    query: str
    results: list[WorkspaceSearchResult] = Field(default_factory=list)


class WorkspaceNoteCreate(NoteCreate):
    pass


class WorkspaceNoteUpdate(NoteUpdate):
    pass
