"""Embedding provider abstraction and async generation service."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.embedding import Embedding
from app.utils.retry import ai_retry


class EmbeddingProvider(Protocol):
    name: str

    async def embed(self, text: str) -> list[float]:
        ...


class OpenAIEmbeddingProvider:
    name = "openai"

    def __init__(self) -> None:
        settings = get_settings()
        if settings.is_sqlite:
            raise ValueError("Embeddings disabled for SQLite local development")
        if not settings.openai_api_key or settings.openai_api_key.startswith("replace_with"):
            raise ValueError("OPENAI_API_KEY required for OpenAI embeddings")
        self._settings = settings
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    @ai_retry()
    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=self._settings.embedding_model,
            input=text,
            dimensions=self._settings.embedding_dimensions,
        )
        return response.data[0].embedding


class EmbeddingGenerationService:
    def __init__(self, provider: EmbeddingProvider | None = None) -> None:
        self.provider = provider or OpenAIEmbeddingProvider()

    async def generate(self, text: str) -> list[float]:
        return await self.provider.embed(text)

    async def upsert_embedding(
        self,
        session: AsyncSession,
        *,
        user_id: UUID,
        source_type: str,
        source_id: UUID,
        content: str,
        metadata: dict | None = None,
    ) -> Embedding:
        vector = await self.generate(content)
        await session.execute(
            delete(Embedding).where(
                Embedding.user_id == user_id,
                Embedding.source_type == source_type,
                Embedding.source_id == source_id,
                Embedding.provider_name == self.provider.name,
            )
        )
        embedding = Embedding(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            content=content,
            embedding=vector,
            provider_name=self.provider.name,
            metadata_=metadata or {},
        )
        session.add(embedding)
        await session.flush()
        return embedding
