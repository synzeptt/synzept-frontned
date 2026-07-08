from pydantic import BaseModel, Field


class ActionCenterActionOut(BaseModel):
    id: str
    title: str
    estimatedTime: str
    priority: str
    reason: str
    completed: bool = False


class ActionCenterOut(BaseModel):
    missionTitle: str
    progress: int
    currentMilestone: str
    actions: list[ActionCenterActionOut] = Field(default_factory=list)
    avoidList: list[str] = Field(default_factory=list)
    aiInsight: str
    momentumScore: int
    weeklyTrend: str
    streak: int
    motivationMessage: str
    openLoops: list[str] = Field(default_factory=list)
    quickActions: list[str] = Field(default_factory=list)
