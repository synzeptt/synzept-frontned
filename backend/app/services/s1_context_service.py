from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.s1 import S1ContextItem, S1ContextOut, S1HomeContext, S1RecommendedAction
from app.services.continue_context_service import ContinueContextService
from app.services.daily_brief_phase8_service import DailyBriefPhase8Service
from app.services.dashboard import DashboardAggregationService
from app.services.user_understanding_service import UserUnderstandingService


class S1ContextService:
    """Stable S1 read model composed from existing Synzept systems.

    This service deliberately owns no new persistence. It keeps V1/V2 models and
    services as the source of truth while giving web and mobile one S1 contract.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_context(self, user: User) -> S1ContextOut:
        dashboard = await DashboardAggregationService(self.session).get_dashboard(user)
        continue_context = await ContinueContextService(self.session).get_context(user)
        daily_brief = await DailyBriefPhase8Service(self.session).today(user.id)
        knows_you = await UserUnderstandingService(self.session).profile_for_user(user)

        personal_os = dashboard.personal_os
        returning = dashboard.returning_user
        mission = personal_os.current_mission or self._first(knows_you.current_mission) or "Choose a mission Synzept can keep visible."
        focus = personal_os.current_focus or self._first(knows_you.current_focus) or "Choose the next meaningful action."

        last_time = [
            S1ContextItem(
                id=item.id,
                title=item.title,
                detail=item.description or "",
                href=item.href,
                source=item.type,
            )
            for item in returning.what_changed[:5]
        ]
        if not last_time:
            last_time = [
                S1ContextItem(
                    id=str(item.id),
                    title=item.title,
                    detail=item.description or "",
                    href=self._activity_href(item.type, item.project_id),
                    source=item.type,
                )
                for item in dashboard.recent_activity[:5]
            ]

        open_loops = [
            S1ContextItem(
                id=item.id,
                title=item.title,
                detail=item.next_step or item.description,
                href=item.href,
                priority=item.priority,
                source=item.type,
            )
            for item in personal_os.open_loops[:6]
        ]
        recommendation = personal_os.suggested_next_action

        return S1ContextOut(
            generated_at=datetime.now(timezone.utc),
            home=S1HomeContext(
                greeting=personal_os.greeting or "Welcome back",
                mission=mission,
                focus=focus,
                last_time=last_time,
                open_loops=open_loops,
                suggested_next_action=S1RecommendedAction(
                    title=recommendation.title,
                    reason=recommendation.reason,
                    href=recommendation.href,
                ),
                is_returning=returning.is_returning,
                days_since_last_seen=returning.days_since_last_seen,
            ),
            continue_context=continue_context,
            daily_brief=daily_brief,
            knows_you=knows_you,
            context_sources={
                **continue_context.context_used,
                "last_time": len(last_time),
                "daily_brief_open_loops": len(daily_brief.get("openLoops", [])),
            },
            capabilities={
                "memory": True,
                "daily_brief": True,
                "continue_system": True,
                "billing": True,
                "notifications": True,
                "platforms": ["web", "mobile"],
            },
        )

    @staticmethod
    def _first(values: list[str]) -> str:
        return values[0] if values else ""

    @staticmethod
    def _activity_href(activity_type: str, project_id) -> str:
        if activity_type == "project" and project_id:
            return f"/projects/{project_id}"
        if activity_type == "conversation":
            return "/chat"
        if activity_type == "task":
            return "/tasks"
        if activity_type == "note":
            return "/notes"
        return "/dashboard"
