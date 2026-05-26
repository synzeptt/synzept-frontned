"""Intent classification and retrieval strategy selection."""

import json
import logging
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.orchestrator.types import ClassifiedIntent, IntentCategory, RetrievalStrategy, ResponseStyle
from app.prompts.templates import INTENT_CLASSIFICATION
from app.services.providers.base import LLMMessage
from app.services.providers.router import LLMRouter
from app.utils.text import tokenize

logger = logging.getLogger(__name__)

# Keyword patterns → intent (fast path)
_PATTERNS: list[tuple[tuple[str, ...], IntentCategory]] = [
    (("briefing", "daily briefing", "focus today", "what should i focus"), IntentCategory.BRIEFING),
    (("summarize", "summary", "recap", "tl;dr"), IntentCategory.SUMMARIZATION),
    (("create task", "add task", "todo:", "to-do", "remind me to"), IntentCategory.TASK_MANAGEMENT),
    (("take a note", "save a note", "note:", "write down"), IntentCategory.NOTE_GENERATION),
    (("help me decide", "should i", "decision", "pros and cons"), IntentCategory.DECISION_SUPPORT),
    (("organize", "structure", "prioritize my", "clean up"), IntentCategory.ORGANIZATION),
    (("brainstorm", "ideas for", "what if", "explore options"), IntentCategory.BRAINSTORMING),
    (("write", "draft", "email", "rewrite", "edit this"), IntentCategory.WRITING),
    (("plan", "roadmap", "strategy", "next steps", "how do i approach"), IntentCategory.PLANNING),
    (("continue", "pick up", "where we left", "last time", "resume"), IntentCategory.CONTINUE),
]


def _strategy_for(category: IntentCategory) -> RetrievalStrategy:
    strategies = {
        IntentCategory.BRIEFING: RetrievalStrategy(memory_limit=8, include_project=True, include_tasks=True),
        IntentCategory.PROJECT_CONTINUE: RetrievalStrategy(memory_limit=8, semantic_limit=6, history_messages=16),
        IntentCategory.CONTINUE: RetrievalStrategy(memory_limit=6, history_messages=18),
        IntentCategory.PLANNING: RetrievalStrategy(memory_limit=6, include_tasks=True, include_project=True),
        IntentCategory.DECISION_SUPPORT: RetrievalStrategy(memory_limit=7, semantic_limit=5),
        IntentCategory.TASK_MANAGEMENT: RetrievalStrategy(memory_limit=4, semantic_limit=3, include_tasks=True),
        IntentCategory.SUMMARIZATION: RetrievalStrategy(memory_limit=5, history_messages=20),
        IntentCategory.WRITING: RetrievalStrategy(memory_limit=4, include_tasks=False, history_messages=12),
        IntentCategory.BRAINSTORMING: RetrievalStrategy(memory_limit=5, semantic_limit=4),
        IntentCategory.NOTE_GENERATION: RetrievalStrategy(memory_limit=5, include_project=True),
        IntentCategory.ORGANIZATION: RetrievalStrategy(memory_limit=6, include_tasks=True),
    }
    return strategies.get(category, RetrievalStrategy())


def _style_for(category: IntentCategory, user_depth: str = "balanced") -> ResponseStyle:
    base_temp = 0.35
    modes = {
        IntentCategory.BRIEFING: ("balanced", 0.25),
        IntentCategory.SUMMARIZATION: ("concise", 0.2),
        IntentCategory.TASK_MANAGEMENT: ("concise", 0.2),
        IntentCategory.WRITING: ("balanced", 0.4),
        IntentCategory.BRAINSTORMING: ("deep", 0.5),
        IntentCategory.PLANNING: ("deep", 0.4),
        IntentCategory.DECISION_SUPPORT: ("deep", 0.35),
        IntentCategory.PROJECT_CONTINUE: ("balanced", 0.35),
    }
    mode, temp = modes.get(category, ("balanced", base_temp))
    if user_depth == "concise":
        mode = "concise"
    elif user_depth == "deep" and mode != "concise":
        mode = "deep"
    return ResponseStyle(mode=mode, temperature=temp)


class IntentClassifier:
    def __init__(self, session: AsyncSession, llm: LLMRouter | None = None) -> None:
        self.session = session
        self.llm = llm or LLMRouter()

    async def classify(
        self,
        user_id: UUID,
        message: str,
        *,
        explicit_project_id: UUID | None = None,
        user_response_depth: str = "balanced",
    ) -> ClassifiedIntent:
        lower = message.lower().strip()

        for keywords, category in _PATTERNS:
            if any(k in lower for k in keywords):
                project_id = explicit_project_id or await self._detect_project(user_id, message)
                return self._build(category, 0.92, project_id, message, user_response_depth)

        project_id = explicit_project_id or await self._detect_project(user_id, message)
        if project_id:
            return self._build(
                IntentCategory.PROJECT_CONTINUE, 0.88, project_id, message, user_response_depth
            )

        if len(message) > 35:
            try:
                return await self._llm_classify(message, explicit_project_id, user_response_depth)
            except Exception as exc:
                logger.debug("LLM intent failed: %s", exc)

        return self._build(
            IntentCategory.GENERAL, 0.75, explicit_project_id, message, user_response_depth
        )

    def _build(
        self,
        category: IntentCategory,
        confidence: float,
        project_id: UUID | None,
        message: str,
        user_depth: str,
    ) -> ClassifiedIntent:
        requires_explicit = category in (
            IntentCategory.TASK_MANAGEMENT,
            IntentCategory.NOTE_GENERATION,
        )
        return ClassifiedIntent(
            category=category,
            confidence=confidence,
            active_project_id=project_id,
            topics=[t for t in tokenize(message) if len(t) > 4][:5],
            retrieval=_strategy_for(category),
            response_style=_style_for(category, user_depth),
            requires_explicit_action=requires_explicit,
        )

    async def _detect_project(self, user_id: UUID, message: str) -> UUID | None:
        result = await self.session.execute(
            select(Project).where(
                Project.user_id == user_id,
                Project.deleted_at.is_(None),
                Project.status == "active",
            )
        )
        lower = message.lower()
        for project in result.scalars().all():
            name = project.name.lower()
            if name in lower:
                return project.id
            name_tokens = set(tokenize(name))
            msg_tokens = set(tokenize(lower))
            if name_tokens & msg_tokens:
                return project.id
        return None

    async def _llm_classify(
        self,
        message: str,
        explicit_project_id: UUID | None,
        user_depth: str,
    ) -> ClassifiedIntent:
        raw = await self.llm.complete(
            [
                LLMMessage(role="system", content=INTENT_CLASSIFICATION),
                LLMMessage(role="user", content=message),
            ],
            temperature=0,
        )
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(match.group(0) if match else raw)
        cat_str = data.get("intent", "general_conversation")
        try:
            category = IntentCategory(cat_str)
        except ValueError:
            category = IntentCategory.GENERAL
        return self._build(
            category,
            float(data.get("confidence", 0.8)),
            explicit_project_id,
            message,
            user_depth,
        )
