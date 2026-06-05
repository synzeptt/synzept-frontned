from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

NodeType = Literal["user", "goal", "project", "memory", "decision", "timeline_event"]


class RelationshipNodeCreate(BaseModel):
    nodeType: NodeType
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=4000)
    entityId: UUID | None = None


class RelationshipNodeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)


class RelationshipNodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    userId: UUID
    nodeType: NodeType
    entityId: UUID | None
    title: str
    description: str
    createdAt: datetime
    updatedAt: datetime


class RelationshipEdgeCreate(BaseModel):
    sourceNodeId: UUID
    targetNodeId: UUID
    relationshipType: str = Field(min_length=1, max_length=80)
    reason: str = Field(default="", max_length=4000)
    strength: float = Field(default=0.5, ge=0, le=1)


class RelationshipEdgeUpdate(BaseModel):
    relationshipType: str | None = Field(default=None, min_length=1, max_length=80)
    reason: str | None = Field(default=None, max_length=4000)
    strength: float | None = Field(default=None, ge=0, le=1)


class RelationshipEdgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    userId: UUID
    sourceNodeId: UUID
    targetNodeId: UUID
    relationshipType: str
    reason: str
    strength: float
    createdAt: datetime
    updatedAt: datetime


class RelationshipGraphOut(BaseModel):
    nodes: list[RelationshipNodeOut]
    edges: list[RelationshipEdgeOut]


class RelationshipNeighborhoodOut(BaseModel):
    node: RelationshipNodeOut
    relatedNodes: list[RelationshipNodeOut]
    edges: list[RelationshipEdgeOut]
