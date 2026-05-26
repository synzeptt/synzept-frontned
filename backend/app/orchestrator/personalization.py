"""Personalization — adapt response style from user profile and preferences."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.orchestrator.types import ClassifiedIntent, ResponseStyle


class PersonalizationEngine:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def enhance_style(self, user_id: UUID, intent: ClassifiedIntent) -> ResponseStyle:
        user = await self.session.get(User, user_id)
        style = intent.response_style
        prefs = (user.preferences or {}) if user else {}

        depth = prefs.get("response_depth", "balanced")
        comm = prefs.get("communication_style", "direct")

        if depth == "concise":
            style.mode = "concise"
            style.temperature = min(style.temperature, 0.3)
        elif depth == "deep":
            style.mode = "deep"
            style.temperature = max(style.temperature, 0.4)

        style.directives = self._build_directives(style.mode, comm, prefs)
        return style

    @staticmethod
    def _build_directives(mode: str, comm: str, prefs: dict) -> str:
        lines = []

        if mode == "concise":
            lines.append("Keep responses concise. Lead with the answer. Use bullets when listing.")
        elif mode == "deep":
            lines.append("Provide thoughtful depth: options, tradeoffs, and clear reasoning when useful.")
        else:
            lines.append("Balance clarity and depth. Be substantive but not verbose.")

        if comm == "strategic":
            lines.append("Frame advice strategically: priorities, sequencing, and outcomes.")
        elif comm == "warm":
            lines.append("Be approachable and clear, without fake enthusiasm or emotional language.")

        habits = prefs.get("work_habits")
        if habits:
            lines.append(f"User work context: {habits}")

        return "\n".join(lines)
