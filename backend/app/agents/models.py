from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    CREATED = "Created"
    PLANNING = "Planning"
    WAITING = "Waiting"
    EXECUTING = "Executing"
    MONITORING = "Monitoring"
    NEEDS_APPROVAL = "Needs Approval"
    COMPLETED = "Completed"
    ARCHIVED = "Archived"


class AgentRuntimeState(BaseModel):
    id: str
    name: str
    objective: str
    currentStep: str
    status: str
    confidence: float
    health: str
    lastActivity: str
    upcomingActions: list[str] = Field(default_factory=list)
    requiresApproval: bool = False
    milestones: list[str] = Field(default_factory=list)
