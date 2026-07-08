from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


ReasoningSeverity = Literal["info", "warning", "attention", "critical"]
ReasoningPriority = Literal["high", "medium", "low"]


class ReasoningInsightOut(BaseModel):
    type: str
    title: str
    detail: str
    severity: ReasoningSeverity = "info"
    priority: ReasoningPriority = "medium"
    source: str = "reasoning"
    confidence: float = 0.65
    evidence: list[str] = Field(default_factory=list)
    project_id: UUID | None = None
    goal_id: UUID | None = None
    task_id: UUID | None = None
    milestone_id: UUID | None = None
    node_id: UUID | None = None


class ReasoningAnalysisOut(BaseModel):
    generated_at: datetime
    confidence_score: float
    suggested_next_action: str | None = None
    highest_priority: str | None = None
    why_it_matters: list[str] = Field(default_factory=list)
    priorities: list[ReasoningInsightOut] = Field(default_factory=list)
    blockers: list[ReasoningInsightOut] = Field(default_factory=list)
    opportunities: list[ReasoningInsightOut] = Field(default_factory=list)
    progress: list[ReasoningInsightOut] = Field(default_factory=list)
    missing_context: list[str] = Field(default_factory=list)
