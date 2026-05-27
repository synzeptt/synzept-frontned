"""Starter workspace seeds that make a new account feel alive immediately."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.memory import Memory
from app.models.message import Message
from app.models.note import Note
from app.models.project import Project
from app.models.user import User


STARTER_PROJECT_TITLE = "Welcome to Synzept"
STARTER_PROJECT_DESCRIPTION = "This workspace evolves with your ideas, projects, and conversations over time."
STARTER_MEMORY = "You're exploring AI-assisted workspaces and long-term project thinking."
STARTER_NOTE = "Synzept remembers your work and helps continue it over time."
STARTER_PROMPT = "How should I structure a startup roadmap?"
STARTER_REPLY = """A useful startup roadmap starts with a small number of living tracks:

1. Clarify the problem you want to make easier.
2. Define the first user who feels that problem sharply.
3. Build the smallest product loop that proves repeat value.
4. Keep a visible list of assumptions, decisions, and next actions.
5. Review the roadmap weekly so it evolves from real evidence instead of stale planning.

I created this starter thread so your Synzept workspace already has a place to continue. As you add notes, projects, and decisions, I can help reconnect them into the next useful step."""


class StarterWorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_for_user(self, user: User, *, focus: str | None = None) -> None:
        if await self._has_seeded_workspace(user.id):
            return

        project = Project(
            user_id=user.id,
            name=STARTER_PROJECT_TITLE,
            description=STARTER_PROJECT_DESCRIPTION,
            status="active",
            context_summary="A starter workspace for preserving ideas, projects, conversations, and decisions over time.",
        )
        self.session.add(project)
        await self.session.flush()

        self.session.add(
            Memory(
                user_id=user.id,
                project_id=project.id,
                memory_type="work",
                category="context",
                content=STARTER_MEMORY,
                summary="Exploring AI-assisted workspaces and long-term project thinking.",
                importance_score=0.82,
                recency_score=1.0,
                metadata_={"source": "starter_workspace", "focus": focus or "startup"},
            )
        )
        self.session.add(
            Note(
                user_id=user.id,
                project_id=project.id,
                title="How Synzept helps",
                content=STARTER_NOTE,
                summary="Synzept preserves working context so future sessions can continue with less restart cost.",
            )
        )

        conversation = Conversation(
            user_id=user.id,
            project_id=project.id,
            title="Structuring a startup roadmap",
            summary="A starter conversation about turning a startup roadmap into focused, revisitable tracks.",
            conversation_type="starter",
            active_intent="Keep startup roadmap thinking connected to projects, notes, and next actions.",
        )
        self.session.add(conversation)
        await self.session.flush()

        self.session.add(
            Message(
                conversation_id=conversation.id,
                role="user",
                content=STARTER_PROMPT,
                metadata_={"source": "starter_workspace"},
            )
        )
        self.session.add(
            Message(
                conversation_id=conversation.id,
                role="assistant",
                content=STARTER_REPLY,
                provider_name="synzept",
                model_name="starter-context",
                metadata_={"source": "starter_workspace"},
            )
        )

        prefs = dict(user.preferences or {})
        onboarding = dict(prefs.get("onboarding", {}))
        onboarding["starter_workspace_seeded"] = True
        onboarding["starter_project_id"] = str(project.id)
        onboarding["onboarding_conversation_id"] = str(conversation.id)
        prefs["onboarding"] = onboarding
        prefs["onboarding_conversation_id"] = str(conversation.id)
        user.preferences = prefs

    async def _has_seeded_workspace(self, user_id) -> bool:
        result = await self.session.execute(
            select(Project.id)
            .where(Project.user_id == user_id, Project.name == STARTER_PROJECT_TITLE, Project.deleted_at.is_(None))
            .limit(1)
        )
        return result.scalar_one_or_none() is not None
