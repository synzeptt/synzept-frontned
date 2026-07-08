from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.chat_intelligence import ChatContextOut, ChatHistorySummaryOut
from app.schemas.dashboard import ReturnRecommendationOut
from app.services.dashboard.aggregation import DashboardAggregationService
from app.services.user_understanding_service import UserUnderstandingService


class ChatIntelligenceService:
    def __init__(self, session) -> None:
        self.session = session

    async def get_context(self, user: User, conversation_id=None, project_id=None) -> ChatContextOut:
        dashboard = await DashboardAggregationService(self.session).get_dashboard(user)
        profile = await UserUnderstandingService(self.session).profile_for_user(user)

        suggested = []
        if profile.next_suggested_actions:
            suggested = [
                ReturnRecommendationOut(
                    title=value,
                    reason="Suggested next action from your current understanding.",
                    href="/chat",
                )
                for value in profile.next_suggested_actions
            ]
        if not suggested and dashboard.personal_os.suggested_next_action:
            suggested = [dashboard.personal_os.suggested_next_action]

        return ChatContextOut(
            who_the_user_is=profile,
            current_mission=dashboard.personal_os.current_mission or (profile.current_mission[0] if profile.current_mission else ""),
            current_focus=dashboard.personal_os.current_focus or (profile.current_focus[0] if profile.current_focus else ""),
            active_projects=dashboard.personal_os.active_projects,
            open_loops=dashboard.personal_os.open_loops,
            recent_progress=dashboard.personal_os.recent_progress,
            recent_decisions=dashboard.personal_os.recent_decisions,
            suggested_next_actions=suggested,
        )

    async def get_history_summary(self, user: User, limit: int = 12) -> list[ChatHistorySummaryOut]:
        result = await self.session.execute(
            Conversation.__table__.select()
            .where(
                Conversation.user_id == user.id,
                Conversation.deleted_at.is_(None),
            )
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        conversations = list(result.scalars().all())
        return [
            ChatHistorySummaryOut(
                conversation_id=conversation.id,
                title=conversation.title,
                summary=conversation.summary,
                active_intent=conversation.active_intent,
                project_id=conversation.project_id,
                updated_at=conversation.updated_at,
            )
            for conversation in conversations
        ]
