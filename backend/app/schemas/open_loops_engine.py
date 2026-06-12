from datetime import datetime
from typing import Literal

from pydantic import BaseModel


OpenLoopType = Literal[
    "unfinished_task",
    "pending_decision",
    "waiting_response",
    "blocked_work",
    "follow_up",
    "incomplete_idea",
]
OpenLoopStatus = Literal["open", "completed", "snoozed", "ignored"]
OpenLoopPriority = Literal["high", "medium", "low"]
OpenLoopSource = Literal["task", "decision", "open_loop", "conversation", "note"]


class OpenLoopEngineItem(BaseModel):
    id: str
    source: OpenLoopSource
    sourceId: str
    title: str
    description: str
    projectId: str | None
    projectName: str
    type: OpenLoopType
    status: OpenLoopStatus
    createdAt: datetime
    updatedAt: datetime
    priority: OpenLoopPriority
    href: str
    nextStep: str


class OpenLoopEngineSummary(BaseModel):
    total: int
    highPriority: int
    pendingDecisions: int
    blockedWork: int
    followUps: int


class OpenLoopEngineOut(BaseModel):
    items: list[OpenLoopEngineItem]
    summary: OpenLoopEngineSummary
