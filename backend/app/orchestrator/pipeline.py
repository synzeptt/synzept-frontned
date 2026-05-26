"""Public orchestrator facade used by chat APIs."""

from collections.abc import AsyncIterator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestrator.orchestrator_service import OrchestratorService


class Orchestrator:
    """Thin wrapper around the context orchestration pipeline."""

    def __init__(self, session: AsyncSession, user_id: UUID) -> None:
        self._brain = OrchestratorService(session, user_id)

    async def run(
        self,
        message: str,
        conversation_id: UUID | None = None,
        project_id: UUID | None = None,
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int = 1200,
    ) -> dict:
        result = await self._brain.run(message, conversation_id, project_id, provider, model, temperature, max_tokens)
        return {
            "conversation_id": result.conversation_id,
            "message_id": result.message_id,
            "reply": result.reply,
            "intent": result.intent.category.value,
            "suggestions": result.suggestions,
        }

    async def stream(
        self,
        message: str,
        conversation_id: UUID | None = None,
        project_id: UUID | None = None,
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int = 1200,
    ) -> AsyncIterator[str]:
        async for chunk in self._brain.stream(message, conversation_id, project_id, provider, model, temperature, max_tokens):
            yield chunk
