from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.home import HomeOut
from app.services.home_context import HomeContextService
from app.services.home_continue_context_engine import ContinueContextEngine
from app.services.home_focus_engine import FocusEngine
from app.services.home_mission_engine import MissionEngine
from app.services.home_open_loop_engine import OpenLoopEngine
from app.services.home_recommendation_engine import RecommendationEngine
from app.services.understanding_engine_service import UnderstandingEngineService


class HomeIntelligenceService:
    """Fast home operating-system read model."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.context = HomeContextService(session)
        self.mission = MissionEngine()
        self.focus = FocusEngine()
        self.open_loops = OpenLoopEngine()
        self.recommendation = RecommendationEngine()
        self.continue_context = ContinueContextEngine()

    async def get_home(self, user: User) -> HomeOut:
        context = await self.context.load(user)
        mission = self.mission.generate(context)
        focus = self.focus.generate(context)
        open_loops = self.open_loops.generate(context)
        action = self.recommendation.generate(context, focus=focus, open_loops=open_loops)
        continue_context = self.continue_context.generate(context, mission=mission, focus=focus, open_loops=open_loops, action=action)
        source_counts = continue_context.sources
        return HomeOut(
            mission=mission,
            focus=focus,
            open_loops=open_loops,
            suggested_action=action,
            continue_context=continue_context,
            generated_at=datetime.now(timezone.utc),
            empty_state=not any(source_counts.values()),
            source_counts=source_counts,
        )

    async def refresh_home(self, user: User) -> HomeOut:
        await UnderstandingEngineService(self.session).refresh(user)
        return await self.get_home(user)
