"""Daily memory consolidation — quality over quantity."""

import hashlib
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory

logger = logging.getLogger(__name__)


class MemoryConsolidation:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def run(self, user_id: UUID) -> dict:
        """
        - Decay importance of stale, rarely accessed memories
        - Soft-delete near-duplicate memories (same content hash)
        """
        result = await self.session.execute(
            select(Memory).where(Memory.user_id == user_id, Memory.deleted_at.is_(None))
        )
        memories = list(result.scalars().all())
        now = datetime.now(timezone.utc)
        decayed = 0
        deduped = 0
        seen_hashes: dict[str, Memory] = {}

        for mem in memories:
            if not mem.content_hash:
                mem.content_hash = hashlib.sha256(" ".join(mem.content.lower().split()).encode()).hexdigest()

            if mem.content_hash in seen_hashes:
                keep = seen_hashes[mem.content_hash]
                if mem.importance > keep.importance:
                    keep, mem = mem, keep
                mem.deleted_at = now
                deduped += 1
            else:
                seen_hashes[mem.content_hash] = mem

            days_idle = 30
            if mem.last_accessed_at:
                days_idle = (now - mem.last_accessed_at).days
            elif mem.created_at:
                days_idle = (now - mem.created_at).days

            if days_idle > 60 and mem.importance > 0.2:
                mem.importance = max(0.2, mem.importance - 0.05)
                decayed += 1

        logger.info(
            "Memory consolidation",
            extra={"user_id": str(user_id), "decayed": decayed, "deduped": deduped},
        )
        return {"decayed": decayed, "deduped": deduped}
