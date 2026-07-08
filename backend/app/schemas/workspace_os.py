from pydantic import BaseModel, Field


class WorkspaceNavItemOut(BaseModel):
    id: str
    label: str
    href: str
    icon: str


class WorkspaceMissionOut(BaseModel):
    id: str
    title: str
    status: str
    progress: int = Field(ge=0, le=100)
    currentMilestone: str
    nextStep: str


class WorkspaceFocusOut(BaseModel):
    title: str
    reason: str
    estimatedTime: str
    linkedItems: list[str] = Field(default_factory=list)


class WorkspaceAgentOut(BaseModel):
    id: str
    name: str
    goal: str
    status: str
    recentActivity: list[str] = Field(default_factory=list)
    plannedNextSteps: list[str] = Field(default_factory=list)
    approvalsAwaitingUser: list[str] = Field(default_factory=list)


class WorkspaceApprovalOut(BaseModel):
    id: str
    title: str
    requestedBy: str
    riskLevel: str
    preview: str
    status: str = "pending"


class WorkspaceKnowledgeOut(BaseModel):
    id: str
    title: str
    kind: str
    summary: str
    source: str
    updatedAt: str


class WorkspaceOpportunityOut(BaseModel):
    id: str
    title: str
    expectedImpact: int = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)
    suggestedAction: str


class WorkspaceOpenLoopOut(BaseModel):
    id: str
    title: str
    owner: str
    dueLabel: str
    urgency: str


class WorkspaceBriefOut(BaseModel):
    headline: str
    whatChanged: list[str] = Field(default_factory=list)
    reminders: list[str] = Field(default_factory=list)
    recommendedNextAction: str


class WorkspaceHomeOut(BaseModel):
    currentMission: WorkspaceMissionOut
    todaysFocus: list[WorkspaceFocusOut] = Field(default_factory=list)
    activeAgents: list[WorkspaceAgentOut] = Field(default_factory=list)
    pendingApprovals: list[WorkspaceApprovalOut] = Field(default_factory=list)
    recentKnowledge: list[WorkspaceKnowledgeOut] = Field(default_factory=list)
    opportunities: list[WorkspaceOpportunityOut] = Field(default_factory=list)
    openLoops: list[WorkspaceOpenLoopOut] = Field(default_factory=list)
    dailyBrief: WorkspaceBriefOut


class WorkspaceSearchResultOut(BaseModel):
    id: str
    type: str
    title: str
    snippet: str
    href: str
    source: str
    updatedAt: str
    tags: list[str] = Field(default_factory=list)


class WorkspaceCommandOut(BaseModel):
    id: str
    title: str
    description: str
    category: str
    shortcut: str | None = None
    requiresInput: bool = False


class WorkspaceOSOut(BaseModel):
    generatedAt: str
    navigation: list[WorkspaceNavItemOut] = Field(default_factory=list)
    home: WorkspaceHomeOut
    searchIndex: list[WorkspaceSearchResultOut] = Field(default_factory=list)
    commands: list[WorkspaceCommandOut] = Field(default_factory=list)
    agents: list[WorkspaceAgentOut] = Field(default_factory=list)
    designPrinciples: list[str] = Field(default_factory=list)


class WorkspaceCommandRunIn(BaseModel):
    commandId: str
    input: str | None = None


class WorkspaceSearchOut(BaseModel):
    query: str
    filters: list[str] = Field(default_factory=list)
    results: list[WorkspaceSearchResultOut] = Field(default_factory=list)
