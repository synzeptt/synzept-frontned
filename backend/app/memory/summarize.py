import logging

from app.prompts.templates import CONVERSATION_SUMMARY, PROJECT_SUMMARY
from app.services.providers.base import LLMMessage
from app.services.providers.router import LLMRouter
from app.utils.text import truncate

logger = logging.getLogger(__name__)


class MemorySummarizer:
    def __init__(self, llm: LLMRouter | None = None) -> None:
        self.llm = llm or LLMRouter()

    async def summarize_conversation(self, messages: list[dict[str, str]]) -> str:
        if len(messages) < 6:
            return ""
        transcript = "\n".join(f"{m['role']}: {m['content']}" for m in messages[-28:])
        try:
            return await self.llm.complete(
                [
                    LLMMessage(role="system", content=CONVERSATION_SUMMARY),
                    LLMMessage(role="user", content=transcript),
                ],
                temperature=0.2,
            )
        except Exception as exc:
            logger.warning("Conversation summary failed: %s", exc)
            return ""

    async def summarize_project(self, project_name: str, notes: list[str], tasks: list[str], memories: list[str]) -> str:
        context = f"Project: {project_name}\n"
        if notes:
            context += "Notes:\n" + "\n".join(f"- {n}" for n in notes[:5]) + "\n"
        if tasks:
            context += "Tasks:\n" + "\n".join(f"- {t}" for t in tasks[:5]) + "\n"
        if memories:
            context += "Memories:\n" + "\n".join(f"- {m}" for m in memories[:5])
        try:
            summary = await self.llm.complete(
                [
                    LLMMessage(role="system", content=PROJECT_SUMMARY),
                    LLMMessage(role="user", content=context),
                ],
                temperature=0.2,
            )
            return truncate(summary, 2000)
        except Exception as exc:
            logger.warning("Project summary failed: %s", exc)
            return ""

    async def compact_old_messages(self, messages: list[dict[str, str]]) -> str:
        """One-line compaction for very long histories."""
        if len(messages) < 20:
            return ""
        older = messages[:-12]
        transcript = "\n".join(f"{m['role']}: {truncate(m['content'], 120)}" for m in older[-20:])
        try:
            return await self.llm.complete(
                [
                    LLMMessage(role="system", content="Compress this older chat into 2 sentences. Be factual."),
                    LLMMessage(role="user", content=transcript),
                ],
                temperature=0.1,
            )
        except Exception:
            return ""
