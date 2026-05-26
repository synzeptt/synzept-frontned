from dataclasses import dataclass, field
from uuid import UUID

from app.models.memory import Memory


@dataclass
class IntentResult:
    intent: str = "chat"
    confidence: float = 0.8
    active_project_id: UUID | None = None
    project_query: str | None = None
    topics: list[str] = field(default_factory=list)


@dataclass
class ScoredMemory:
    memory: Memory
    score: float
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    recency_score: float = 0.0
    project_score: float = 0.0

    @property
    def content(self) -> str:
        return self.memory.content


@dataclass
class SemanticHit:
    source_type: str
    source_id: UUID
    content: str
    score: float


@dataclass
class ProjectContext:
    project_id: UUID
    name: str
    summary: str
    notes: list[str] = field(default_factory=list)
    tasks: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)


@dataclass
class ContextPayload:
    """Optimized context selected for prompt assembly."""

    intent: IntentResult
    user_profile: str = ""
    conversation_summary: str = ""
    active_intent: str = ""
    short_term_messages: list[dict[str, str]] = field(default_factory=list)
    long_term_memories: list[str] = field(default_factory=list)
    project_context: ProjectContext | None = None
    semantic_snippets: list[str] = field(default_factory=list)
    tasks_snapshot: str = ""
    daily_context: str = ""
    trimmed_message_count: int = 0
