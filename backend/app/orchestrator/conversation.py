"""Conversation analysis for continuity and context needs."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestrator.types import ConversationAnalysis
from app.services.chat_service import ChatService


class ConversationAnalyzer:
    def __init__(self, session: AsyncSession) -> None:
        self.chat = ChatService(session)

    async def analyze(
        self, user_id: UUID, conversation_id: UUID, user_message: str
    ) -> ConversationAnalysis:
        messages = await self.chat.get_messages(conversation_id)
        conv = await self.chat.get_conversation(user_id, conversation_id)
        lower = user_message.lower()
        follow_up_phrases = ("continue", "as we discussed", "what about", "next", "also", "that")
        is_follow_up = len(messages) > 2 and any(p in lower for p in follow_up_phrases)

        return ConversationAnalysis(
            message_count=len(messages),
            has_summary=bool(conv and conv.summary),
            needs_continuity=is_follow_up or len(messages) > 6,
            is_follow_up=is_follow_up,
            thread_topic=conv.summary[:120] if conv and conv.summary else "",
        )
