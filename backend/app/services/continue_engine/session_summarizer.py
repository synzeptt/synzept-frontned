from sqlalchemy import select
from app.models.conversation import Conversation


class SessionSummarizer:
    def __init__(self, session) -> None:
        self.session = session

    async def last_session_summary(self, user_id, limit=1):
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None))
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        conversations = list(result.scalars().all())
        if not conversations:
            return None
        c = conversations[0]
        return {
            "conversation_id": c.id,
            "title": c.title,
            "summary": c.summary,
            "active_intent": c.active_intent,
            "updated_at": c.updated_at,
        }
