"""Backward-compatible retriever delegating to pipeline."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.pipeline import MemoryRetrievalPipeline


class MemoryRetriever:
    def __init__(self, session: AsyncSession, embeddings=None) -> None:
        self.pipeline = MemoryRetrievalPipeline(session)
        self.session = session

    async def get_relevant(self, user_id: UUID, query: str, limit: int = 8, project_id=None) -> list:
        _, scored, _ = await self.pipeline.run(user_id, query, project_id=project_id)
        return [s.memory for s in scored[:limit]]
