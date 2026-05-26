import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class SemanticSearch:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._embeddings: EmbeddingService | None = None
        try:
            self._embeddings = EmbeddingService()
        except ValueError:
            pass

    async def search(self, user_id: UUID, query: str, limit: int = 6) -> list[str]:
        if not self._embeddings:
            return []
        try:
            hits = await self._embeddings.search(self.session, user_id=user_id, query=query, limit=limit)
            return [f"[{source}] {content}" for source, content, _ in hits]
        except Exception as exc:
            logger.warning("Semantic search failed: %s", exc)
            return []
