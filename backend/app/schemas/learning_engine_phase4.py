from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.knows_you import LearningSuggestionOut


class LearningObservationCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    source: str = Field(default="manual", min_length=1, max_length=80)


class LearningObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    userId: UUID
    source: str
    content: str
    status: str
    createdAt: datetime
    updatedAt: datetime


class LearningAnalysisOut(BaseModel):
    observationsAnalyzed: int
    suggestionsCreated: int
    suggestions: list[LearningSuggestionOut]


class LearningEngineOut(BaseModel):
    observations: list[LearningObservationOut]
    suggestions: list[LearningSuggestionOut]
