from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_execution import ActionExecution
from app.models.learning import LearningSuggestion
from app.models.user import User
from app.models.user_understanding import UserUnderstanding


class ActionLearningService:
    """Turns completed actions into approval-ready user understanding suggestions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_completion(self, action: ActionExecution) -> list[LearningSuggestion]:
        if not action.output and not action.request:
            return []
        user = await self.session.get(User, action.user_id)
        if not user:
            return []
        suggestions = self._build_suggestions(action)
        if not suggestions:
            return []
        await self._persist_understanding(action, suggestions)
        existing = await self._existing_titles(action.user_id)
        created: list[LearningSuggestion] = []
        for suggestion in suggestions:
            if suggestion["title"] in existing:
                continue
            item = LearningSuggestion(
                user_id=action.user_id,
                title=suggestion["title"],
                description=suggestion["description"],
                confidence=suggestion["confidence"],
                status="pending",
            )
            self.session.add(item)
            created.append(item)
        await self.session.flush()
        return created

    async def promote_to_understanding(self, user_id: UUID, suggestion_id: UUID) -> UserUnderstanding:
        from app.services.learning_engine_service import LearningEngineService

        return await LearningEngineService(self.session).accept_suggestion(user_id, suggestion_id)

    async def _existing_titles(self, user_id: UUID) -> set[str]:
        result = await self.session.execute(select(LearningSuggestion).where(LearningSuggestion.user_id == user_id))
        return {item.title for item in result.scalars()}

    async def _persist_understanding(self, action: ActionExecution, suggestions: list[dict[str, Any]]) -> None:
        for suggestion in suggestions:
            title = suggestion["title"]
            existing = await self.session.execute(
                select(UserUnderstanding).where(
                    UserUnderstanding.user_id == action.user_id,
                    UserUnderstanding.source == "learned",
                    UserUnderstanding.title == title,
                )
            )
            item = existing.scalar_one_or_none()
            if item is None:
                self.session.add(
                    UserUnderstanding(
                        user_id=action.user_id,
                        category=self._category_for_title(title),
                        title=title,
                        value=suggestion["description"],
                        source="learned",
                        confidence=suggestion["confidence"],
                        learned_at=datetime.now(timezone.utc),
                    )
                )
                continue
            item.category = self._category_for_title(title)
            item.value = suggestion["description"]
            item.confidence = suggestion["confidence"]
            item.learned_at = datetime.now(timezone.utc)
        await self.session.flush()

    @staticmethod
    def _category_for_title(title: str) -> str:
        lower = title.casefold()
        if any(token in lower for token in ["prefers", "structured", "summary", "calendar", "schedule"]):
            return "preferences"
        if "workflow" in lower:
            return "habits"
        return "learned_insights"

    def _build_suggestions(self, action: ActionExecution) -> list[dict[str, Any]]:
        request = (action.request or "").strip()
        output = (action.output or "").strip()
        worker_id = ((action.metadata_ or {}).get("worker_result") or {}).get("worker_id") if isinstance(action.metadata_, dict) else None
        lower_request = request.casefold()
        lower_output = output.casefold()
        suggestions: list[dict[str, Any]] = []

        if any(token in lower_request for token in ["concise", "bullet", "summary", "brief", "weekly review", "executive"]):
            suggestions.append({
                "title": "Prefers concise responses",
                "description": "You often ask for concise, structured outputs with the clearest next step first.",
                "confidence": 0.78,
            })

        if any(token in lower_output for token in ["executive summary", "summary", "bullet", "key findings"]):
            suggestions.append({
                "title": "Prefers structured summaries",
                "description": "You tend to favor structured summaries with bullet points that make the core point obvious quickly.",
                "confidence": 0.74,
            })

        if worker_id == "writing" or "draft" in lower_request or "write" in lower_request:
            suggestions.append({
                "title": "Workflow: draft before send",
                "description": "You usually want a draft prepared before finalizing a message or report.",
                "confidence": 0.71,
            })

        if any(token in lower_request for token in ["calendar", "meeting", "schedule"]):
            suggestions.append({
                "title": "Prefers calendar-aware planning",
                "description": "You often want scheduling decisions grounded in calendar context and availability.",
                "confidence": 0.69,
            })

        return suggestions
