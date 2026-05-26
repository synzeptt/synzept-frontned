"""Retrieval layer — delegates to ContextEngine."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.context_engine import ContextEngine
from app.prompts.builder import ContextBundle, PromptBuilder


class ContextAssembler:
    """Assembles optimized context before LLM generation."""

    def __init__(self, session: AsyncSession) -> None:
        self.engine = ContextEngine(session)
        self.prompts = PromptBuilder()

    async def assemble(
        self,
        *,
        user_id: UUID,
        query: str,
        conversation_id: UUID,
        project_id: UUID | None,
    ) -> ContextBundle:
        payload = await self.engine.build(
            user_id=user_id,
            query=query,
            conversation_id=conversation_id,
            project_id=project_id,
        )
        return ContextBundle(
            user_profile=payload.user_profile,
            project_context=self._format_project(payload),
            memories=payload.long_term_memories,
            recent_messages=payload.short_term_messages,
            semantic_hits=payload.semantic_snippets,
            conversation_summary=payload.conversation_summary,
            tasks_snapshot=payload.tasks_snapshot,
        )

    def build_messages(self, payload) -> list:
        from app.memory.types import ContextPayload

        if isinstance(payload, ContextPayload):
            return self.prompts.build_from_payload(payload)
        return PromptBuilder().build(payload)

    @staticmethod
    def _format_project(payload) -> str:
        if not payload.project_context:
            return ""
        p = payload.project_context
        return f"{p.name}\n{p.summary}"
