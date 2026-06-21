from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.s1 import S1ContextItem, S1HomeContext, S1HomeOut, S1RecommendedAction
from app.services.home_intelligence_service import HomeIntelligenceService


class S1HomeService:
    """Compatibility adapter over the Home Intelligence Layer."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_home(self, user: User) -> S1HomeOut:
        generated = await HomeIntelligenceService(self.session).get_home(user)
        open_loops = [
            S1ContextItem(id=item.id, title=item.title, detail=item.detail, href=item.href, priority=item.priority, source=item.source)
            for item in generated.open_loops
        ]
        last_time = [
            S1ContextItem(id=item.id, title=item.title, detail=item.detail, href=item.href, priority=item.priority, source=item.source)
            for item in generated.continue_context.cards
        ]
        action = S1RecommendedAction(
            title=generated.suggested_action.title,
            reason=generated.suggested_action.reason,
            href=generated.suggested_action.href,
        )
        home = S1HomeContext(
            greeting=f"Welcome back{', ' + user.display_name if user.display_name else ''}.",
            mission=generated.mission,
            focus=generated.focus,
            last_time=last_time,
            open_loops=open_loops,
            suggested_next_action=action,
        )
        return S1HomeOut(
            generated_at=generated.generated_at or datetime.now(timezone.utc),
            home=home,
            continue_prompt=generated.continue_context.prompt,
            context_sources=generated.source_counts,
        )
