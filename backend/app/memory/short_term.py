"""Short-term memory: recent messages + active session intent with intelligent trimming."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.constants import MAX_SHORT_TERM_MESSAGES, SHORT_TERM_CHAR_BUDGET
from app.models.conversation import Conversation
from app.models.message import Message
from app.utils.text import truncate


class ShortTermMemory:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_context(
        self,
        conversation_id: UUID,
        *,
        exclude_last_user: bool = False,
    ) -> tuple[list[dict[str, str]], str, int]:
        """
        Returns (trimmed_messages, active_intent, trimmed_count).
        Uses conversation summary + recent messages; trims by recency and char budget.
        """
        conv = await self.session.get(Conversation, conversation_id)
        active_intent = getattr(conv, "active_intent", None) or "" if conv else ""

        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        rows = list(result.scalars().all())

        if exclude_last_user and rows and rows[-1].role == "user":
            rows = rows[:-1]

        messages = [{"role": m.role, "content": m.content} for m in rows]
        trimmed, dropped = self._trim_messages(messages)
        return trimmed, active_intent, dropped

    async def update_active_intent(self, conversation_id: UUID, intent: str) -> None:
        conv = await self.session.get(Conversation, conversation_id)
        if conv and intent:
            conv.active_intent = truncate(intent, 400)

    def _trim_messages(self, messages: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
        if not messages:
            return [], 0

        # Keep most recent messages up to count limit
        recent = messages[-MAX_SHORT_TERM_MESSAGES:]
        dropped = len(messages) - len(recent)

        # Trim by character budget from the end (most recent preserved)
        total_chars = sum(len(m["content"]) for m in recent)
        while total_chars > SHORT_TERM_CHAR_BUDGET and len(recent) > 2:
            removed = recent.pop(0)
            total_chars -= len(removed["content"])
            dropped += 1

        return recent, dropped
