"""User context graph — rolling profile synthesis from durable memories."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.constants import MEMORY_TYPE_LONG, MEMORY_TYPE_PROJECT
from app.models.memory import Memory
from app.models.user import User
from app.utils.text import truncate

logger = logging.getLogger(__name__)


class UserContextGraph:
    """
    Maintains a lightweight user context graph via profile_summary.
    Updated after memory extraction — not on every message.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def refresh(self, user_id: UUID, max_memories: int = 12) -> None:
        user = await self.session.get(User, user_id)
        if not user:
            return

        result = await self.session.execute(
            select(Memory)
            .where(
                Memory.user_id == user_id,
                Memory.deleted_at.is_(None),
                Memory.memory_type.in_([MEMORY_TYPE_LONG, MEMORY_TYPE_PROJECT]),
            )
            .order_by(Memory.importance.desc(), Memory.access_count.desc())
            .limit(max_memories)
        )
        memories = list(result.scalars().all())
        if not memories:
            return

        by_category: dict[str, list[str]] = {}
        for m in memories:
            by_category.setdefault(m.category, []).append(m.content)

        lines = []
        for category, items in sorted(by_category.items()):
            lines.append(f"{category}: " + "; ".join(items[:3]))

        synthesized = truncate("\n".join(lines), 1200)
        if synthesized and synthesized != (user.profile_summary or ""):
            user.profile_summary = synthesized
            logger.debug("Updated user context graph for %s", user_id)
