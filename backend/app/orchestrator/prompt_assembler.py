"""Intent-aware prompt assembly with personalization and continuity."""

from app.memory.types import ContextPayload
from app.orchestrator.types import ClassifiedIntent, ConversationAnalysis, IntentCategory, ResponseStyle
from app.prompts.templates import (
    CONTINUITY_INSTRUCTION,
    INTENT_INSTRUCTIONS,
    SYNZEPT_SYSTEM,
)
from app.services.providers.base import LLMMessage
from app.utils.text import truncate


class PromptAssembler:
    def assemble(
        self,
        payload: ContextPayload,
        intent: ClassifiedIntent,
        style: ResponseStyle,
        conversation: ConversationAnalysis,
    ) -> list[LLMMessage]:
        sections: list[str] = [SYNZEPT_SYSTEM.strip()]

        intent_key = intent.category.value
        if intent_key in INTENT_INSTRUCTIONS:
            sections.append(INTENT_INSTRUCTIONS[intent_key])

        if style.directives:
            sections.append(f"## Response style\n{style.directives}")

        if conversation.needs_continuity and conversation.has_summary:
            sections.append(
                CONTINUITY_INSTRUCTION.format(
                    summary=truncate(payload.conversation_summary or conversation.thread_topic, 400)
                )
            )

        if payload.user_profile:
            sections.append(f"## User\n{truncate(payload.user_profile, 400)}")

        if payload.project_context:
            p = payload.project_context
            block = f"## Active project: {p.name}\n{truncate(p.summary, 650)}"
            if p.tasks:
                block += "\nOpen tasks:\n" + "\n".join(f"- {t}" for t in p.tasks[:5])
            if p.notes:
                block += "\nRelevant notes:\n" + "\n".join(f"- {n}" for n in p.notes[:4])
            if p.decisions:
                block += "\nKey decisions:\n" + "\n".join(f"- {d}" for d in p.decisions[:3])
            sections.append(block)

        if payload.conversation_summary and not conversation.needs_continuity:
            sections.append(f"## Thread\n{truncate(payload.conversation_summary, 400)}")

        if payload.active_intent:
            sections.append(f"## Current focus\n{truncate(payload.active_intent, 180)}")

        memory_budget = 1600 if style.mode == "concise" else 2000
        if payload.long_term_memories:
            sections.append(
                f"## Relevant memory\n{self._join(payload.long_term_memories, memory_budget)}"
            )

        sem_budget = 900 if intent.category == IntentCategory.WRITING else 1200
        if payload.semantic_snippets:
            sections.append(f"## Related context\n{self._join(payload.semantic_snippets, sem_budget)}")

        if payload.daily_context:
            sections.append(f"## Today\n{truncate(payload.daily_context, 500)}")

        if payload.tasks_snapshot and intent.retrieval.include_tasks:
            sections.append(f"## Tasks & goals\n{truncate(payload.tasks_snapshot, 450)}")

        sections.append(
            "## Rules\n"
            "- Use only provided context; never invent past events\n"
            "- Be calm, clear, and actionable; no fake emotions or hype\n"
            "- Do not create tasks/notes unless the user explicitly asks"
        )

        messages: list[LLMMessage] = [LLMMessage(role="system", content="\n\n".join(sections))]

        history_limit = intent.retrieval.history_messages
        for msg in payload.short_term_messages[-history_limit:]:
            if msg["role"] in ("user", "assistant"):
                messages.append(LLMMessage(role=msg["role"], content=msg["content"]))

        return messages

    @staticmethod
    def _join(items: list[str], max_chars: int) -> str:
        lines: list[str] = []
        total = 0
        for item in items:
            line = f"- {item}"
            if total + len(line) > max_chars:
                break
            lines.append(line)
            total += len(line)
        return "\n".join(lines)
