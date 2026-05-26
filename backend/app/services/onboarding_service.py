"""Onboarding flow - profile capture, memory init, first chat, workspace seed."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.memory.store import MemoryStore
from app.models.conversation import Conversation
from app.models.memory import Memory
from app.models.note import Note
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.user_profile import UserProfile
from app.orchestrator.pipeline import Orchestrator
from app.schemas.onboarding import (
    OnboardingCompleteOut,
    OnboardingContextIn,
    OnboardingDashboardPreview,
    OnboardingFirstChatIn,
    OnboardingFirstChatOut,
    OnboardingStatusOut,
    OnboardingWorkspaceIn,
)
from app.schemas.task import TaskCreate
from app.services.daily_summary_service import DailySummaryService
from app.services.embedding_service import EmbeddingService
from app.services.onboarding import OnboardingAnalytics
from app.services.user_profile_service import UserProfileService
from app.tasks.service import TaskService
from app.utils.text import truncate

logger = logging.getLogger(__name__)

STATE_NEW = "new"
STATE_WELCOME = "welcome"
STATE_CONTEXT = "context"
STATE_WORKSPACE = "workspace"
STATE_MEMORIES = "memories"
STATE_FIRST_CHAT = "first_chat"
STATE_COMPLETE = "complete"

STEP_ORDER = ["welcome", "profile", "workspace", "memory", "first_chat", "dashboard", "complete"]


class OnboardingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.profiles = UserProfileService(session)
        self.analytics = OnboardingAnalytics(session)
        try:
            self._embeddings = EmbeddingService()
        except ValueError:
            self._embeddings = None
        self.memory_store = MemoryStore(session, self._embeddings)

    async def get_status(self, user: User) -> OnboardingStatusOut:
        profile = await self.profiles.get_or_create(user.id)
        mem_count = await self._memory_count(user.id)
        project_count = await self._project_count(user.id)
        conv_id = await self._onboarding_conversation_id(user.id)
        prefs = self._prefs(user)
        onboarding = self._onboarding_meta(user)
        completed_steps = onboarding.get("completed_steps", [])
        skipped_steps = onboarding.get("skipped_steps", [])

        initialized_systems = list(onboarding.get("initialized_systems", []))
        if mem_count and "memory" not in initialized_systems:
            initialized_systems.append("memory")
        if project_count and "workspace" not in initialized_systems:
            initialized_systems.append("workspace")
        if conv_id and "first_ai_interaction" not in initialized_systems:
            initialized_systems.append("first_ai_interaction")

        return OnboardingStatusOut(
            state=user.onboarding_state,
            is_complete=user.onboarding_state == STATE_COMPLETE,
            display_name=user.display_name,
            goals=list(profile.goals or [])[:5],
            has_memories=mem_count > 0,
            has_workspace=project_count > 0,
            conversation_id=conv_id,
            completed_steps=completed_steps,
            skipped_steps=skipped_steps,
            initialized_systems=initialized_systems,
            resume_step=self._resume_step(user, completed_steps),
            dashboard_preview=self._dashboard_preview(profile, bool(project_count), bool(mem_count)),
            analytics=await self.analytics.summary(user.id, prefs),
        )

    async def mark_welcome(self, user: User) -> OnboardingStatusOut:
        if user.onboarding_state == STATE_NEW:
            user.onboarding_state = STATE_WELCOME
        self._mark_step(user, "welcome", initialized="welcome_flow", resume_step="profile")
        await self.analytics.track(user_id=user.id, event_type="onboarding_started", step="welcome")
        return await self.get_status(user)

    async def save_context(self, user: User, data: OnboardingContextIn) -> OnboardingStatusOut:
        profile = await self.profiles.get_or_create(user.id)

        user.display_name = data.display_name.strip()
        if data.timezone:
            user.timezone = data.timezone

        depth = data.communication_style
        user.preferences = {
            **self._prefs(user),
            "response_depth": depth,
            "communication_style": "strategic" if depth == "deep" else "direct",
        }

        profile.display_name = user.display_name
        profile.timezone = user.timezone
        profile.communication_style = depth
        profile.goals = [g.strip() for g in data.goals if g.strip()][:5]
        profile.work_preferences = {
            "primary_role": data.primary_role,
            "work_type": data.work_type,
        }
        profile.communication_preferences = {
            "style": user.preferences.get("communication_style", "direct"),
            "response_depth": depth,
        }
        profile.productivity_style = data.productivity_style
        profile.routines = {"priorities": data.current_priorities[:5]}

        summary_parts = []
        if data.primary_role:
            summary_parts.append(f"Role: {data.primary_role}")
        if data.work_type:
            summary_parts.append(f"Work type: {data.work_type}")
        if profile.goals:
            summary_parts.append("Goals: " + "; ".join(profile.goals))
        if data.current_priorities:
            summary_parts.append("Priorities: " + "; ".join(data.current_priorities[:3]))
        user.profile_summary = truncate("\n".join(summary_parts), 500) if summary_parts else None
        profile.summary = user.profile_summary

        user.onboarding_state = STATE_CONTEXT
        self._mark_step(user, "profile", initialized="profile", resume_step="workspace")
        await self.analytics.track(
            user_id=user.id,
            event_type="onboarding_profile_saved",
            step="profile",
            metadata={"goals": len(profile.goals), "priorities": len(data.current_priorities)},
        )
        return await self.get_status(user)

    async def save_workspace(self, user: User, data: OnboardingWorkspaceIn) -> OnboardingStatusOut:
        profile = await self.profiles.get_or_create(user.id)
        skipped = data.skipped or not any(
            [data.create_project, data.project_name, data.first_goal, data.first_task, data.first_note]
        )
        if skipped:
            self._skip_step(user, "workspace")
            self._mark_step(user, "workspace", resume_step="memory")
            user.onboarding_state = STATE_WORKSPACE
            await self.analytics.track(user_id=user.id, event_type="onboarding_workspace_skipped", step="workspace")
            return await self.get_status(user)

        project = await self._ensure_starter_project(
            user,
            profile,
            name=data.project_name or data.first_goal or data.first_task,
            description=data.project_description,
        )
        tasks_created = 0
        if data.first_goal and data.first_goal not in (profile.goals or []):
            profile.goals = [data.first_goal, *(profile.goals or [])][:5]
        if data.first_task:
            await TaskService(self.session).create(
                user.id,
                TaskCreate(
                    title=data.first_task,
                    description="Added during onboarding",
                    priority="high",
                    project_id=project.id if project else None,
                ),
            )
            tasks_created += 1
        if data.first_note:
            self.session.add(
                Note(
                    user_id=user.id,
                    project_id=project.id if project else None,
                    title="Onboarding note",
                    content=data.first_note,
                    summary=truncate(data.first_note, 240),
                )
            )
            await self.session.flush()

        self._mark_step(user, "workspace", initialized="workspace", resume_step="memory")
        if project:
            self._set_onboarding_value(user, "first_project_id", str(project.id))
        user.onboarding_state = STATE_WORKSPACE
        await self.analytics.track(
            user_id=user.id,
            event_type="onboarding_workspace_seeded",
            step="workspace",
            metadata={"project_created": bool(project), "tasks_created": tasks_created, "note_created": bool(data.first_note)},
        )
        return await self.get_status(user)

    async def initialize_memories(self, user: User) -> OnboardingStatusOut:
        profile = await self.profiles.get_or_create(user.id)
        created = 0

        async def create_once(content: str, category: str, importance: float) -> None:
            nonlocal created
            if await self._memory_exists(user.id, content):
                return
            await self.memory_store.create(
                user_id=user.id,
                content=content,
                category=category,
                importance=importance,
            )
            created += 1

        if profile.goals:
            for goal in profile.goals[:3]:
                await create_once(f"User goal: {goal}", "goals", 0.85)

        priorities = (profile.routines or {}).get("priorities") or []
        for priority in priorities[:3]:
            await create_once(f"Current priority: {priority}", "productivity", 0.8)

        depth = (profile.communication_preferences or {}).get("response_depth", "balanced")
        await create_once(f"Prefers {depth} responses - clear, calm, and actionable.", "preferences", 0.75)

        if (profile.work_preferences or {}).get("primary_role"):
            await create_once(f"Works as: {profile.work_preferences['primary_role']}", "work", 0.7)

        if user.display_name:
            await create_once(f"User's name is {user.display_name}.", "identity", 0.9)

        user.onboarding_state = STATE_MEMORIES
        self._mark_step(user, "memory", initialized="memory", resume_step="first_chat")
        await self.analytics.track(
            user_id=user.id,
            event_type="onboarding_memory_initialized",
            step="memory",
            metadata={"memories_created": created},
            value=created,
        )
        logger.info("Onboarding memories initialized", extra={"user_id": str(user.id), "count": created})
        return await self.get_status(user)

    async def first_interaction(self, user: User, body: OnboardingFirstChatIn) -> OnboardingFirstChatOut:
        profile = await self.profiles.get_or_create(user.id)
        project = await self._ensure_starter_project(user, profile)

        if body.message and body.message.strip():
            prompt = body.message.strip()
        elif body.use_suggested_prompt:
            goals = ", ".join(profile.goals[:2]) if profile.goals else "my goals"
            priorities = ", ".join(((profile.routines or {}).get("priorities") or [])[:2]) or "today's work"
            style = (profile.communication_preferences or {}).get("response_depth", "balanced")
            prompt = (
                "I just finished onboarding in Synzept. Use only the profile, memory, project, and priority context available to you. "
                f"My goals include {goals}; my current priorities include {priorities}; "
                f"I prefer {style} responses. Give me a calm, specific first-use plan: what to focus on first, "
                "what to capture as memory, and how to keep momentum without adding clutter."
            )
        else:
            raise AppError("Message required", status_code=400, code="message_required")

        result = await Orchestrator(self.session, user.id).run(
            prompt,
            conversation_id=await self._onboarding_conversation_id(user.id),
            project_id=project.id if project else None,
        )

        user.onboarding_state = STATE_FIRST_CHAT
        self._mark_step(user, "first_chat", initialized="first_ai_interaction", resume_step="dashboard")
        self._set_onboarding_value(user, "onboarding_conversation_id", str(result["conversation_id"]))
        prefs = self._prefs(user)
        prefs["onboarding_conversation_id"] = str(result["conversation_id"])
        user.preferences = prefs
        await self.analytics.track(
            user_id=user.id,
            event_type="onboarding_first_ai_success",
            step="first_chat",
            metadata={"conversation_id": str(result["conversation_id"])},
        )

        return OnboardingFirstChatOut(
            conversation_id=result["conversation_id"],
            reply=result["reply"],
            suggestions=result.get("suggestions", []),
        )

    async def complete(self, user: User) -> OnboardingCompleteOut:
        profile = await self.profiles.get_or_create(user.id)
        project = await self._ensure_starter_project(user, profile)
        task_svc = TaskService(self.session)

        tasks_created = 0
        priorities = (profile.routines or {}).get("priorities") or profile.goals or []
        existing_titles = await self._task_titles(user.id)
        for i, item in enumerate(priorities[:3]):
            if item in existing_titles:
                continue
            await task_svc.create(
                user.id,
                TaskCreate(
                    title=item[:300],
                    description="Added during onboarding",
                    priority="high" if i == 0 else "medium",
                    project_id=project.id if project else None,
                ),
            )
            tasks_created += 1

        mem_count = await self._memory_count(user.id)

        try:
            await DailySummaryService(self.session).generate_for_user(user.id)
        except Exception as exc:
            logger.warning("Daily summary on onboarding complete failed: %s", exc)

        user.onboarding_state = STATE_COMPLETE
        profile.onboarding_completed = True
        self._mark_step(user, "dashboard", initialized="dashboard", resume_step="complete")
        self._mark_step(user, "complete", initialized="completion_tracking", resume_step="complete")
        conv_id = await self._onboarding_conversation_id(user.id)

        welcome = (
            f"Welcome{', ' + user.display_name if user.display_name else ''}. "
            "Your workspace is ready. Synzept will remember your goals and help you stay organized."
        )
        await self.analytics.track(
            user_id=user.id,
            event_type="onboarding_completed",
            step="complete",
            metadata={"tasks_created": tasks_created, "memories_created": mem_count, "project_id": str(project.id) if project else None},
        )

        return OnboardingCompleteOut(
            state=STATE_COMPLETE,
            project_id=project.id if project else None,
            tasks_created=tasks_created,
            memories_created=mem_count,
            conversation_id=conv_id,
            welcome_message=welcome,
            dashboard_preview=self._dashboard_preview(profile, bool(project), bool(mem_count)),
            analytics=await self.analytics.summary(user.id, self._prefs(user)),
        )

    async def skip_to_complete(self, user: User) -> OnboardingCompleteOut:
        """Recover interrupted onboarding - seed a minimal workspace."""
        if user.onboarding_state == STATE_COMPLETE:
            return OnboardingCompleteOut(
                state=STATE_COMPLETE,
                welcome_message="Onboarding already complete.",
                analytics=await self.analytics.summary(user.id, self._prefs(user)),
            )
        profile = await self.profiles.get_or_create(user.id)
        if not user.display_name:
            user.display_name = profile.display_name or user.email.split("@")[0]
        if user.onboarding_state in (STATE_NEW, STATE_WELCOME):
            user.onboarding_state = STATE_CONTEXT
        self._skip_step(user, self._resume_step(user, self._onboarding_meta(user).get("completed_steps", [])))
        if user.onboarding_state in (STATE_CONTEXT, STATE_WORKSPACE):
            await self.initialize_memories(user)
        await self.analytics.track(user_id=user.id, event_type="onboarding_skipped_to_complete", step="skip")
        return await self.complete(user)

    async def _ensure_starter_project(
        self,
        user: User,
        profile: UserProfile,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> Project | None:
        existing = await self.session.execute(
            select(Project).where(Project.user_id == user.id, Project.deleted_at.is_(None)).limit(1)
        )
        project = existing.scalar_one_or_none()
        if project:
            return project

        project_name = (name or (profile.goals[0] if profile.goals else "My workspace"))[:80]
        if len(project_name.strip()) < 3:
            project_name = "My workspace"

        project = Project(
            user_id=user.id,
            name=project_name.strip(),
            description=description or "Your primary focus area in Synzept.",
            status="active",
            context_summary=user.profile_summary,
        )
        self.session.add(project)
        await self.session.flush()
        return project

    async def _memory_count(self, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Memory).where(Memory.user_id == user_id, Memory.deleted_at.is_(None))
        )
        return int(result.scalar() or 0)

    async def _project_count(self, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Project).where(Project.user_id == user_id, Project.deleted_at.is_(None))
        )
        return int(result.scalar() or 0)

    async def _memory_exists(self, user_id: UUID, content: str) -> bool:
        result = await self.session.execute(
            select(Memory.id).where(Memory.user_id == user_id, Memory.deleted_at.is_(None), Memory.content == content).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _task_titles(self, user_id: UUID) -> set[str]:
        result = await self.session.execute(select(Task.title).where(Task.user_id == user_id, Task.deleted_at.is_(None)))
        return set(result.scalars().all())

    async def _onboarding_conversation_id(self, user_id: UUID) -> UUID | None:
        user = await self.session.get(User, user_id)
        if not user:
            return None
        raw = (user.preferences or {}).get("onboarding_conversation_id") or (
            (user.preferences or {}).get("onboarding", {}).get("onboarding_conversation_id")
        )
        if raw:
            try:
                return UUID(raw)
            except ValueError:
                pass
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None))
            .order_by(Conversation.created_at.desc())
            .limit(1)
        )
        conv = result.scalar_one_or_none()
        return conv.id if conv else None

    @staticmethod
    def _prefs(user: User) -> dict:
        return dict(user.preferences or {})

    def _onboarding_meta(self, user: User) -> dict:
        return dict(self._prefs(user).get("onboarding", {}))

    def _set_onboarding_value(self, user: User, key: str, value) -> None:
        prefs = self._prefs(user)
        onboarding = dict(prefs.get("onboarding", {}))
        onboarding[key] = value
        prefs["onboarding"] = onboarding
        user.preferences = prefs

    def _mark_step(
        self,
        user: User,
        step: str,
        *,
        initialized: str | None = None,
        resume_step: str | None = None,
    ) -> None:
        prefs = self._prefs(user)
        onboarding = dict(prefs.get("onboarding", {}))
        completed = list(onboarding.get("completed_steps", []))
        if step not in completed:
            completed.append(step)
        systems = list(onboarding.get("initialized_systems", []))
        if initialized and initialized not in systems:
            systems.append(initialized)
        onboarding["completed_steps"] = completed
        onboarding["initialized_systems"] = systems
        onboarding["resume_step"] = resume_step or self._next_step(completed)
        prefs["onboarding"] = onboarding
        user.preferences = prefs

    def _skip_step(self, user: User, step: str) -> None:
        prefs = self._prefs(user)
        onboarding = dict(prefs.get("onboarding", {}))
        skipped = list(onboarding.get("skipped_steps", []))
        if step and step not in skipped:
            skipped.append(step)
        onboarding["skipped_steps"] = skipped
        prefs["onboarding"] = onboarding
        user.preferences = prefs

    @staticmethod
    def _next_step(completed_steps: list[str]) -> str:
        completed = set(completed_steps)
        return next((step for step in STEP_ORDER if step not in completed), "complete")

    def _resume_step(self, user: User, completed_steps: list[str]) -> str:
        onboarding = self._onboarding_meta(user)
        if user.onboarding_state == STATE_COMPLETE:
            return "complete"
        return onboarding.get("resume_step") or self._next_step(completed_steps)

    @staticmethod
    def _dashboard_preview(profile: UserProfile, has_workspace: bool, has_memories: bool) -> OnboardingDashboardPreview:
        goals = list(profile.goals or [])
        priorities = list((profile.routines or {}).get("priorities") or [])
        suggested = (priorities or goals or ["Choose one focus for today"])
        structure = ["Daily focus", "Active projects", "Memory context" if has_memories else "Memory foundation"]
        if has_workspace:
            structure.insert(1, "Starter project")
        summary = "Synzept is ready to keep today focused around your current work."
        if not goals and not priorities:
            summary = "Synzept will start light and help shape priorities as you go."
        next_actions = ["Review suggested priorities", "Open your starter project"]
        return OnboardingDashboardPreview(
            suggested_priorities=suggested,
            starter_structure=structure[:5],
            continuity_summary=summary,
            next_actions=next_actions,
        )
