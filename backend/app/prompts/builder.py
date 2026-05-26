from dataclasses import dataclass

from app.memory.types import ContextPayload
from app.prompts.templates import SYNZEPT_SYSTEM
from app.services.providers.base import LLMMessage
from app.utils.text import truncate


@dataclass
class ContextBundle:
    """Legacy bundle for backward compatibility."""

    user_profile: str = ""
    project_context: str = ""
    memories: list[str] | None = None
    recent_messages: list[dict[str, str]] | None = None
    semantic_hits: list[str] | None = None
    conversation_summary: str = ""
    tasks_snapshot: str = ""
    max_memory_chars: int = 2000
    max_semantic_chars: int = 1500
    max_history_messages: int = 16


class PromptBuilder:
    def build(self, bundle: ContextBundle) -> list[LLMMessage]:
        payload = ContextPayload(
            user_profile=bundle.user_profile,
            conversation_summary=bundle.conversation_summary,
            short_term_messages=bundle.recent_messages or [],
            long_term_memories=bundle.memories or [],
            semantic_snippets=bundle.semantic_hits or [],
            tasks_snapshot=bundle.tasks_snapshot,
        )
        if bundle.project_context:
            from app.memory.types import ProjectContext
            from uuid import UUID

            payload.project_context = ProjectContext(
                project_id=UUID(int=0),
                name="Project",
                summary=bundle.project_context,
            )
        return self.build_from_payload(payload)

    def build_from_payload(self, payload: ContextPayload) -> list[LLMMessage]:
        sections: list[str] = [SYNZEPT_SYSTEM.strip()]

        if payload.user_profile:
            sections.append(f"## User\n{truncate(payload.user_profile, 400)}")

        if payload.project_context:
            p = payload.project_context
            project_block = f"## Active project: {p.name}\n{truncate(p.summary, 600)}"
            if p.tasks:
                project_block += "\nOpen tasks:\n" + "\n".join(f"- {t}" for t in p.tasks[:4])
            if p.notes:
                project_block += "\nNotes:\n" + "\n".join(f"- {n}" for n in p.notes[:3])
            sections.append(project_block)

        if payload.conversation_summary:
            sections.append(f"## Conversation thread\n{truncate(payload.conversation_summary, 450)}")

        if payload.active_intent:
            sections.append(f"## Current focus\n{truncate(payload.active_intent, 200)}")

        if payload.long_term_memories:
            mem_text = self._join_lines(payload.long_term_memories, 1800)
            sections.append(f"## What you know about the user\n{mem_text}")

        if payload.semantic_snippets:
            sem_text = self._join_lines(payload.semantic_snippets, 1200)
            sections.append(f"## Related context\n{sem_text}")

        if payload.tasks_snapshot:
            sections.append(f"## Active tasks\n{truncate(payload.tasks_snapshot, 450)}")

        messages: list[LLMMessage] = [LLMMessage(role="system", content="\n\n".join(sections))]

        for msg in payload.short_term_messages:
            if msg["role"] in ("user", "assistant"):
                messages.append(LLMMessage(role=msg["role"], content=msg["content"]))

        return messages

    @staticmethod
    def _join_lines(items: list[str], max_chars: int) -> str:
        lines: list[str] = []
        total = 0
        for item in items:
            line = f"- {item}"
            if total + len(line) > max_chars:
                break
            lines.append(line)
            total += len(line)
        return "\n".join(lines)
