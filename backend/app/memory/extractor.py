"""Long-term memory extraction with strict meaningful-only storage."""

import json
import logging
import re

from app.memory.constants import CATEGORIES
from app.prompts.templates import MEMORY_EXTRACT
from app.services.providers.base import LLMMessage
from app.services.providers.router import LLMRouter

logger = logging.getLogger(__name__)


class MemoryExtractor:
    def __init__(self, llm: LLMRouter | None = None) -> None:
        self.llm = llm or LLMRouter()

    async def extract(self, user_message: str, assistant_reply: str) -> dict | None:
        """
        Returns None if nothing worth storing.
        Otherwise: {content, category, importance, action: create|update|skip}
        """
        # Fast pre-filter: skip trivial exchanges
        if self._is_trivial(user_message, assistant_reply):
            return None

        try:
            raw = await self.llm.complete(
                [
                    LLMMessage(role="system", content=MEMORY_EXTRACT),
                    LLMMessage(
                        role="user",
                        content=f"User: {user_message}\nAssistant: {assistant_reply}",
                    ),
                ],
                temperature=0,
            )
            data = self._parse(raw)
            if not data or not data.get("keep"):
                return None
            content = (data.get("content") or "").strip()
            if len(content) < 8:
                return None
            category = self._normalize_category(data.get("category", "other"))
            importance = min(max(float(data.get("importance", 0.6)), 0.3), 1.0)
            return {
                "content": content,
                "category": category,
                "importance": importance,
                "action": data.get("action", "create"),
            }
        except Exception as exc:
            logger.debug("Memory extraction failed: %s", exc)
            return None

    @staticmethod
    def _is_trivial(user_message: str, assistant_reply: str) -> bool:
        um = user_message.strip().lower()
        if len(um) < 12:
            return True
        trivial_starts = ("hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "yes", "no")
        if um.split()[0] in trivial_starts and len(um.split()) < 4:
            return True
        if len(assistant_reply) < 30:
            return True
        return False

    @staticmethod
    def _parse(raw: str) -> dict | None:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        return json.loads(match.group(0))

    @staticmethod
    def _normalize_category(category: str) -> str:
        cat = (category or "other").lower().strip()
        mapping = {
            "goal": "goals",
            "preference": "preferences",
            "habit": "routines",
            "workflow": "productivity_patterns",
            "productivity": "productivity_patterns",
            "idea": "projects",
            "project": "projects",
            "decision": "decisions",
        }
        cat = mapping.get(cat, cat)
        return cat if cat in CATEGORIES else "other"
