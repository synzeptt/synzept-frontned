import json
import logging
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.types import IntentResult
from app.models.project import Project
from app.prompts.templates import INTENT_ANALYSIS
from app.services.providers.base import LLMMessage
from app.services.providers.router import LLMRouter
from app.utils.text import tokenize

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    """Analyze user intent and detect active project references."""

    def __init__(self, session: AsyncSession, llm: LLMRouter | None = None) -> None:
        self.session = session
        self.llm = llm or LLMRouter()

    async def analyze(self, user_id: UUID, message: str, explicit_project_id: UUID | None = None) -> IntentResult:
        lower = message.lower().strip()

        if any(k in lower for k in ("briefing", "daily briefing", "what should i focus")):
            return IntentResult(intent="briefing", confidence=0.95)

        if any(k in lower for k in ("create task", "add task", "todo:", "to-do")):
            return IntentResult(intent="task", confidence=0.9, active_project_id=explicit_project_id)

        project_id = explicit_project_id or await self._detect_project(user_id, message)
        if project_id:
            return IntentResult(
                intent="project_continue",
                confidence=0.85,
                active_project_id=project_id,
                topics=self._extract_topics(message),
            )

        if any(k in lower for k in ("continue", "pick up", "where we left", "last time")):
            return IntentResult(intent="continue", confidence=0.8, active_project_id=explicit_project_id)

        # Lightweight LLM intent for ambiguous cases (skipped if message is very short)
        if len(message) > 40:
            try:
                llm_intent = await self._llm_intent(message)
                llm_intent.active_project_id = llm_intent.active_project_id or explicit_project_id
                return llm_intent
            except Exception as exc:
                logger.debug("LLM intent fallback: %s", exc)

        return IntentResult(intent="chat", confidence=0.7, active_project_id=explicit_project_id)

    async def _detect_project(self, user_id: UUID, message: str) -> UUID | None:
        result = await self.session.execute(
            select(Project).where(Project.user_id == user_id, Project.deleted_at.is_(None), Project.status == "active")
        )
        projects = list(result.scalars().all())
        lower = message.lower()
        for project in projects:
            name = project.name.lower()
            if name in lower or any(token in name for token in tokenize(message) if len(token) > 3):
                return project.id
        return None

    async def _llm_intent(self, message: str) -> IntentResult:
        raw = await self.llm.complete(
            [
                LLMMessage(role="system", content=INTENT_ANALYSIS),
                LLMMessage(role="user", content=message),
            ],
            temperature=0,
        )
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(match.group(0) if match else raw)
        return IntentResult(
            intent=data.get("intent", "chat"),
            confidence=float(data.get("confidence", 0.7)),
            topics=data.get("topics") or [],
        )

    @staticmethod
    def _extract_topics(message: str) -> list[str]:
        return [t for t in tokenize(message) if len(t) > 4][:5]
