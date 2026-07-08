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


class FeatureUsageOut(BaseModel):
    feature: str
    events: int = 0
    users: int = 0
    timeSpentSeconds: int = 0


class RetentionOut(BaseModel):
    signupCohort: int = 0
    returnedUsers: int = 0
    retentionRate: float = 0
    day1: float = 0
    day7: float = 0
    day30: float = 0


class OnboardingMilestonesOut(BaseModel):
    signupCompleted: int = 0
    firstChat: int = 0
    firstMemory: int = 0
    firstReturnVisit: int = 0
    onboardingCompleted: int = 0


class FounderUsersOut(BaseModel):
    totalUsers: int = 0
    newUsers: int = 0
    activeUsers: int = 0


class FounderActivationOut(BaseModel):
    completedOnboarding: int = 0
    createdFirstMission: int = 0
    returnedNextDay: int = 0
    completedOnboardingRate: float = 0
    createdFirstMissionRate: float = 0
    returnedNextDayRate: float = 0


class FeedbackSignalOut(BaseModel):
    id: str | None = None
    title: str
    detail: str
    category: str
    feedback_type: str
    sentiment: str
    status: str
    votes: int = 0
    demand_score: int = 0


class FeedbackCategoryOut(BaseModel):
    category: str
    count: int


class FeedbackProductInsightsOut(BaseModel):
    what_users_want: list[FeedbackSignalOut] = Field(default_factory=list)
    what_users_dislike: list[FeedbackSignalOut] = Field(default_factory=list)
    what_users_like: list[FeedbackSignalOut] = Field(default_factory=list)
    what_should_be_prioritized: list[FeedbackSignalOut] = Field(default_factory=list)


class FeedbackAnalyticsOut(BaseModel):
    total: int = 0
    user_sentiment: str = "neutral"
    sentiment_score: int = 0
    categories: list[FeedbackCategoryOut] = Field(default_factory=list)
    most_requested_features: list[FeedbackSignalOut] = Field(default_factory=list)
    most_common_frustrations: list[FeedbackSignalOut] = Field(default_factory=list)
    most_common_compliments: list[FeedbackSignalOut] = Field(default_factory=list)
    emerging_trends: list[FeedbackSignalOut] = Field(default_factory=list)
    top_reported_issues: list[FeedbackSignalOut] = Field(default_factory=list)
    product_insights: FeedbackProductInsightsOut = Field(default_factory=FeedbackProductInsightsOut)


class FounderAlertOut(BaseModel):
    title: str
    detail: str
    severity: str = "medium"
    metric: str = ""


class ProductAnalyticsOut(BaseModel):
    windowDays: int
    users: FounderUsersOut = Field(default_factory=FounderUsersOut)
    activation: FounderActivationOut = Field(default_factory=FounderActivationOut)
    metrics: list[AnalyticsMetric] = Field(default_factory=list)
    funnel: list[AnalyticsFunnelStep] = Field(default_factory=list)
    dropOffs: list[AnalyticsDropOff] = Field(default_factory=list)
    daily: list[AnalyticsDailyPoint] = Field(default_factory=list)
    feedback: FeedbackAnalyticsOut = Field(default_factory=FeedbackAnalyticsOut)
    mostUsedFeatures: list[FeatureUsageOut] = Field(default_factory=list)
    leastUsedFeatures: list[FeatureUsageOut] = Field(default_factory=list)
    confusingAreas: list[FeedbackSignalOut] = Field(default_factory=list)
    founderAlerts: list[FounderAlertOut] = Field(default_factory=list)
    retention: RetentionOut = Field(default_factory=RetentionOut)
    onboarding: OnboardingMilestonesOut = Field(default_factory=OnboardingMilestonesOut)
