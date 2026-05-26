"""Orchestration intelligence types."""

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from app.memory.types import ContextPayload, IntentResult


class IntentCategory(StrEnum):
    GENERAL = "general_conversation"
    PLANNING = "planning"
    WRITING = "writing"
    BRAINSTORMING = "brainstorming"
    TASK_MANAGEMENT = "task_management"
    PROJECT_CONTINUE = "project_continuation"
    SUMMARIZATION = "summarization"
    DECISION_SUPPORT = "decision_support"
    ORGANIZATION = "organization"
    NOTE_GENERATION = "note_generation"
    BRIEFING = "briefing"
    CONTINUE = "continue"


@dataclass
class RetrievalStrategy:
    memory_limit: int = 6
    semantic_limit: int = 5
    include_project: bool = True
    include_tasks: bool = True
    history_messages: int = 14


@dataclass
class ResponseStyle:
    mode: str = "balanced"  # concise | balanced | deep
    temperature: float = 0.35
    max_tokens_hint: int = 1200
    directives: str = ""


@dataclass
class ConversationAnalysis:
    message_count: int = 0
    has_summary: bool = False
    needs_continuity: bool = False
    is_follow_up: bool = False
    thread_topic: str = ""


@dataclass
class ClassifiedIntent:
    category: IntentCategory
    confidence: float = 0.8
    active_project_id: UUID | None = None
    topics: list[str] = field(default_factory=list)
    retrieval: RetrievalStrategy = field(default_factory=RetrievalStrategy)
    response_style: ResponseStyle = field(default_factory=ResponseStyle)
    requires_explicit_action: bool = False

    @property
    def legacy_intent(self) -> IntentResult:
        return IntentResult(
            intent=self.category.value,
            confidence=self.confidence,
            active_project_id=self.active_project_id,
            topics=self.topics,
        )


@dataclass
class ActionSuggestion:
    type: str  # task | note | prioritize | summarize | plan | review
    label: str
    description: str
    requires_confirmation: bool = True


@dataclass
class IntelligenceResult:
    conversation_id: UUID
    message_id: UUID | None
    reply: str
    intent: ClassifiedIntent
    suggestions: list[ActionSuggestion] = field(default_factory=list)
    context_used: ContextPayload | None = None
