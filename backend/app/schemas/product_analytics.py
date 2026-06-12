from pydantic import BaseModel, Field


class AnalyticsMetric(BaseModel):
    key: str
    label: str
    value: int
    previous: int = 0
    change: int = 0


class AnalyticsFunnelStep(BaseModel):
    key: str
    label: str
    count: int
    conversionFromPrevious: float | None = None


class AnalyticsDailyPoint(BaseModel):
    date: str
    signups: int = 0
    logins: int = 0
    activeUsers: int = 0
    projectsCreated: int = 0
    dailyBriefViews: int = 0
    openLoopViews: int = 0
    upgradeClicks: int = 0
    checkoutStarts: int = 0
    successfulPayments: int = 0


class AnalyticsDropOff(BaseModel):
    label: str
    fromStep: str
    toStep: str
    lost: int
    dropOffRate: float


class ProductAnalyticsOut(BaseModel):
    windowDays: int
    metrics: list[AnalyticsMetric] = Field(default_factory=list)
    funnel: list[AnalyticsFunnelStep] = Field(default_factory=list)
    dropOffs: list[AnalyticsDropOff] = Field(default_factory=list)
    daily: list[AnalyticsDailyPoint] = Field(default_factory=list)
