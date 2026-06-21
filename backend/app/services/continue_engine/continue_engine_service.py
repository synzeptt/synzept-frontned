from app.services.continue_engine.session_summarizer import SessionSummarizer
from app.services.continue_engine.open_loop_detector import OpenLoopDetector
from app.services.continue_engine.recommendation_engine import RecommendationEngine
from app.services.continue_engine.builder import ContinueContextBuilder
from app.services.user_understanding_service import UserUnderstandingService


class ContinueEngineService:
    def __init__(self, session) -> None:
        self.session = session

    async def get_continue(self, user):
        builder = ContinueContextBuilder(self.session)
        context = await builder.build(user)
        summarizer = SessionSummarizer(self.session)
        last = await summarizer.last_session_summary(user.id)
        return {"last_session": last, "continue_context": context}

    async def refresh(self, user):
        # Refresh user understanding from memories as part of refresh
        created, coverage = await UserUnderstandingService(self.session).sync_from_memories(user.id)
        # return rebuilt continue context
        return await self.get_continue(user)
