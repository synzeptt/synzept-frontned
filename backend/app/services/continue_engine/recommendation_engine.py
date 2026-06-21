from app.services.user_understanding_service import UserUnderstandingService
from app.services.dashboard.aggregation import DashboardAggregationService


class RecommendationEngine:
    def __init__(self, session) -> None:
        self.session = session

    async def recommend(self, user):
        profile = await UserUnderstandingService(self.session).profile_for_user(user)
        if profile.next_suggested_actions:
            return profile.next_suggested_actions[0]
        dashboard = await DashboardAggregationService(self.session).get_dashboard(user)
        if dashboard.personal_os and dashboard.personal_os.suggested_next_action:
            return dashboard.personal_os.suggested_next_action.title
        return "Choose one meaningful priority for today."
