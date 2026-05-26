"""Lightweight intent analysis for orchestration strategy."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.utils.text import tokenize


class OrchestrationIntentCategory(StrEnum):
    CONVERSATION = "conversation"
    PLANNING = "planning"
    BRAINSTORMING = "brainstorming"
    ORGANIZATION = "organization"
    PROJECT_CONTINUATION = "project_continuation"
    SUMMARIZATION = "summarization"
    TASK_ASSISTANCE = "task_assistance"
    NOTE_GENERATION = "note_generation"


@dataclass(slots=True)
class IntentStrategy:
    memory_limit: int = 6
    recent_message_limit: int = 12
    include_project: bool = True
    include_tasks: bool = True
    max_prompt_tokens: int = 5200
    temperature: float = 0.35


@dataclass(slots=True)
class OrchestrationIntent:
    category: OrchestrationIntentCategory
    confidence: float
    topics: list[str] = field(default_factory=list)
    strategy: IntentStrategy = field(default_factory=IntentStrategy)


class IntentService:
    _patterns: tuple[tuple[tuple[str, ...], OrchestrationIntentCategory, float], ...] = (
        (
            (
                "continue",
                "resume",
                "pick up",
                "where we left",
                "yesterday's",
                "last discussion",
                "what were my priorities",
                "what was i working on",
                "restore context",
            ),
            OrchestrationIntentCategory.PROJECT_CONTINUATION,
            0.9,
        ),
        (("summarize", "summary", "recap", "tl;dr"), OrchestrationIntentCategory.SUMMARIZATION, 0.92),
        (("create task", "add task", "todo:", "to-do", "prioritize task"), OrchestrationIntentCategory.TASK_ASSISTANCE, 0.92),
        (("take a note", "save a note", "note:", "write down"), OrchestrationIntentCategory.NOTE_GENERATION, 0.9),
        (("organize", "structure", "clean up", "sort out"), OrchestrationIntentCategory.ORGANIZATION, 0.88),
        (("brainstorm", "ideas", "explore options", "what if"), OrchestrationIntentCategory.BRAINSTORMING, 0.88),
        (("plan", "roadmap", "strategy", "next steps", "approach"), OrchestrationIntentCategory.PLANNING, 0.86),
    )

    async def classify(self, message: str, *, has_active_project: bool = False) -> OrchestrationIntent:
        lower = message.lower()
        for keywords, category, confidence in self._patterns:
            if any(keyword in lower for keyword in keywords):
                return self._build(category, confidence, message)
        if has_active_project and self._looks_like_followup(lower):
            return self._build(OrchestrationIntentCategory.PROJECT_CONTINUATION, 0.82, message)
        return self._build(OrchestrationIntentCategory.CONVERSATION, 0.74, message)

    def _build(
        self,
        category: OrchestrationIntentCategory,
        confidence: float,
        message: str,
    ) -> OrchestrationIntent:
        return OrchestrationIntent(
            category=category,
            confidence=confidence,
            topics=[token for token in tokenize(message) if len(token) > 4][:6],
            strategy=self._strategy(category),
        )

    @staticmethod
    def _strategy(category: OrchestrationIntentCategory) -> IntentStrategy:
        strategies = {
            OrchestrationIntentCategory.CONVERSATION: IntentStrategy(memory_limit=4, recent_message_limit=10),
            OrchestrationIntentCategory.PLANNING: IntentStrategy(memory_limit=7, recent_message_limit=14, temperature=0.4),
            OrchestrationIntentCategory.BRAINSTORMING: IntentStrategy(memory_limit=6, recent_message_limit=12, temperature=0.55),
            OrchestrationIntentCategory.ORGANIZATION: IntentStrategy(memory_limit=6, recent_message_limit=14),
            OrchestrationIntentCategory.PROJECT_CONTINUATION: IntentStrategy(memory_limit=8, recent_message_limit=18),
            OrchestrationIntentCategory.SUMMARIZATION: IntentStrategy(memory_limit=4, recent_message_limit=22, include_tasks=False, temperature=0.2),
            OrchestrationIntentCategory.TASK_ASSISTANCE: IntentStrategy(memory_limit=5, recent_message_limit=12, include_tasks=True, temperature=0.25),
            OrchestrationIntentCategory.NOTE_GENERATION: IntentStrategy(memory_limit=5, recent_message_limit=16, temperature=0.25),
        }
        return strategies[category]

    @staticmethod
    def _looks_like_followup(message: str) -> bool:
        followup_terms = ("that", "this", "it", "same", "continue", "next", "resume", "roadmap", "strategy")
        return any(term in message for term in followup_terms)
