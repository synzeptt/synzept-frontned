"""Onboarding flow - profile capture, memory init, first chat, workspace seed."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.memory.store import MemoryStore
from app.models.conversation import Conversation
from app.models.goal import Goal
from app.models.memory import Memory
from app.models.note import Note
from app.models.project import Project
from app.models.project_intelligence_phase2 import OpenLoop
from app.models.task import Task
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.user_understanding import UserUnderstanding
from app.orchestrator.pipeline import Orchestrator
from app.schemas.onboarding import (
    FirstRunIntelligenceIn,
    OnboardingCompleteOut,
    OnboardingContextIn,
    OnboardingDashboardPreview,
    OnboardingFirstChatIn,
    OnboardingFirstChatOut,
    OnboardingStatusOut,
    OnboardingWorkspaceIn,
)
from app.schemas.goal import GoalCreate
from app.schemas.task import TaskCreate
from app.services.autonomous_workspace_service import AutonomousWorkspaceService
from app.services.daily_brief_phase8_service import DailyBriefPhase8Service
from app.services.daily_summary_service import DailySummaryService
from app.services.embedding_service import EmbeddingService
from app.services.goal_progress_service import GoalProgressService
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

    async def complete_first_run_intelligence(self, user: User, data: FirstRunIntelligenceIn) -> OnboardingCompleteOut:
        profile = await self.profiles.get_or_create(user.id)
        name = user.display_name or profile.display_name or user.email.split("@")[0]
        goals = data.top_goals or [data.building]
        project_names = data.important_projects or [data.building]
        current_mission = (data.generated_current_mission or f"Build {data.building}").strip()
        current_focus = data.current_focus.strip()
        first_open_loop_titles = data.generated_open_loops or [
            f"Turn {current_focus} into a concrete next action",
            f"Resolve the blocker: {data.struggling_with}" if data.struggling_with else f"Define first milestone for {goals[0] if goals else data.building}",
            f"Track progress toward: {data.success_90_days[:120]}",
        ]
        first_suggested_actions = data.generated_suggested_actions or [
            f"Spend 25 minutes on: {current_focus}",
            f"Write the next visible milestone for {goals[0] if goals else data.building}",
        ]

        user.display_name = name
        user.profile_summary = truncate(
            "\n".join(
                [
                    f"Current mission: {current_mission}",
                    f"Current focus: {current_focus}",
                    "Top goals: " + "; ".join(goals[:5]),
                    f"Current blocker: {data.struggling_with}" if data.struggling_with else "",
                    f"Help continue: {data.help_continue}" if data.help_continue else "",
                    f"90-day success: {data.success_90_days}",
                ]
            ),
            700,
        )
        profile.display_name = name
        profile.goals = goals[:5]
        profile.summary = user.profile_summary
        profile.routines = {"priorities": [current_focus, *first_suggested_actions, *goals[:3]][:5]}
        profile.work_preferences = {
            "primary_role": data.building,
            "work_type": "first_run_intelligence",
            "current_blocker": data.struggling_with,
            "help_continue": data.help_continue,
        }

        projects = await self._seed_first_run_projects(user, project_names, current_focus, data.success_90_days)
        goals_created = await self._seed_first_run_goals(user.id, goals, projects, data.success_90_days)
        open_loops = await self._seed_first_run_open_loops(projects, goals, current_focus, data.success_90_days, first_open_loop_titles)
        await self._seed_first_run_understanding(
            user.id,
            current_mission=current_mission,
            current_focus=current_focus,
            goals=goals,
            projects=projects,
            open_loops=open_loops,
            success_90_days=data.success_90_days,
            first_suggested_actions=first_suggested_actions,
            struggling_with=data.struggling_with,
            help_continue=data.help_continue,
        )
        await self.initialize_memories(user)

        first_goal = goals_created[0] if goals_created else None
        if first_goal:
            try:
                await AutonomousWorkspaceService(self.session).goal_to_plan(user.id, first_goal.id, create_structure=True)
            except Exception as exc:
                logger.warning("First-run autonomous plan generation failed: %s", exc)

        weekly = await AutonomousWorkspaceService(self.session).weekly_plan(user.id)
        try:
            await DailyBriefPhase8Service(self.session).refresh(user.id)
        except Exception as exc:
            logger.warning("First-run daily brief generation failed: %s", exc)
        weekly_actions = [item.title for item in weekly.this_week[:4]]
        first_actions = list(dict.fromkeys([*first_suggested_actions, *weekly_actions]))[:5] or [
            f"Clarify the first milestone for {goals[0]}",
            f"Spend 25 minutes moving {current_focus} forward",
        ]
        first_daily_brief = {
            "greeting": f"Good Morning, {name}",
            "whatChanged": "Synzept created your first operating context from your answers.",
            "whatMattersToday": current_focus,
            "openLoopsRequiringAttention": [loop.title for loop in open_loops[:5]],
            "recommendedNextAction": first_actions[0] if first_actions else current_focus,
            "focusForToday": current_focus,
        }
        welcome_brief = {
            "currentMission": current_mission,
            "currentFocus": current_focus,
            "topGoals": goals[:5],
            "activeProjects": [project.name for project in projects[:5]],
            "openLoops": [loop.title for loop in open_loops[:5]],
            "suggestedFirstActions": first_actions,
            "dailyBrief": first_daily_brief,
            "initialWeeklyPlan": {
                "thisWeek": [item.title for item in weekly.this_week[:5]],
                "nextWeek": [item.title for item in weekly.next_week[:5]],
                "priorityFocus": weekly.priority_focus or current_focus,
            },
            "success90Days": data.success_90_days,
        }

        prefs = self._prefs(user)
        onboarding = dict(prefs.get("onboarding", {}))
        onboarding["first_run_intelligence"] = data.model_dump()
        onboarding["welcome_brief"] = welcome_brief
        prefs["onboarding"] = onboarding
        user.preferences = prefs

        user.onboarding_state = STATE_COMPLETE
        profile.onboarding_completed = True
        self._mark_step(user, "profile", initialized="profile", resume_step="workspace")
        self._mark_step(user, "workspace", initialized="workspace", resume_step="memory")
        self._mark_step(user, "memory", initialized="memory", resume_step="dashboard")
        self._mark_step(user, "dashboard", initialized="dashboard", resume_step="complete")
        self._mark_step(user, "complete", initialized="first_run_intelligence", resume_step="complete")
        await self.analytics.track(
            user_id=user.id,
            event_type="first_run_intelligence_completed",
            step="complete",
            metadata={"goals": len(goals), "projects": len(projects), "open_loops": len(open_loops)},
        )
        await self.analytics.track(
            user_id=user.id,
            event_type="first_run_activation_completed",
            step="activation",
            metadata={
                "generated": ["current_mission", "current_focus", "open_loops", "suggested_actions", "daily_brief", "active_projects", "weekly_plan"],
                "goals": len(goals),
                "projects": len(projects),
                "open_loops": len(open_loops),
                "first_actions": len(first_actions),
            },
        )

        return OnboardingCompleteOut(
            state=STATE_COMPLETE,
            project_id=projects[0].id if projects else None,
            tasks_created=sum(len(goal.milestones[0].tasks) for goal in goals_created if goal.milestones),
            memories_created=await self._memory_count(user.id),
            conversation_id=await self._onboarding_conversation_id(user.id),
            welcome_message=f"Welcome, {name}. Synzept has built your first workspace around {current_mission}.",
            welcome_brief=welcome_brief,
            dashboard_preview=OnboardingDashboardPreview(
                suggested_priorities=goals[:5],
                starter_structure=["Current Mission", "Active Projects", "Open Loops", "Initial Weekly Plan"],
                continuity_summary=f"Synzept is ready to guide {current_mission} with focus on {current_focus}.",
                next_actions=first_actions,
            ),
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

    async def _seed_first_run_projects(
        self,
        user: User,
        project_names: list[str],
        current_focus: str,
        success_90_days: str,
    ) -> list[Project]:
        existing_result = await self.session.execute(
            select(Project).where(Project.user_id == user.id, Project.deleted_at.is_(None))
        )
        existing_by_name = {project.name.casefold(): project for project in existing_result.scalars()}
        projects: list[Project] = []
        for index, name in enumerate(project_names[:5]):
            key = name.casefold()
            project = existing_by_name.get(key)
            if not project:
                project = Project(
                    user_id=user.id,
                    name=name[:200],
                    description=f"First-run project for: {success_90_days}",
                    status="active",
                    current_focus=current_focus if index == 0 else f"Move {name} forward.",
                    recommended_next_step=f"Define the next concrete action for {name}.",
                    context_summary=f"Created during first-run intelligence. 90-day success: {success_90_days}",
                )
                self.session.add(project)
                await self.session.flush()
            else:
                project.status = "active"
                project.current_focus = project.current_focus or current_focus
                project.recommended_next_step = project.recommended_next_step or f"Define the next concrete action for {name}."
                project.context_summary = project.context_summary or f"90-day success: {success_90_days}"
            projects.append(project)
        return projects

    async def _seed_first_run_goals(self, user_id: UUID, goals: list[str], projects: list[Project], success_90_days: str) -> list[Goal]:
        service = GoalProgressService(self.session)
        existing = await service.list_goals(user_id)
        existing_titles = {goal.title.casefold(): goal for goal in existing}
        created: list[Goal] = []
        primary_project = projects[0] if projects else None
        for title in goals[:5]:
            goal = existing_titles.get(title.casefold())
            if not goal:
                goal = await service.create_goal(
                    user_id,
                    GoalCreate(
                        title=title,
                        description=f"Created from first-run onboarding. 90-day success: {success_90_days}",
                        project_id=primary_project.id if primary_project else None,
                    ),
                )
            created.append(goal)
        return created

    async def _seed_first_run_open_loops(
        self,
        projects: list[Project],
        goals: list[str],
        current_focus: str,
        success_90_days: str,
        loop_titles: list[str] | None = None,
    ) -> list[OpenLoop]:
        if not projects:
            return []
        project = projects[0]
        titles = (loop_titles or [
            f"Turn {current_focus} into a concrete next action",
            f"Define first milestone for {goals[0] if goals else project.name}",
            f"Track 90-day success: {success_90_days[:120]}",
        ])[:5]
        existing = await self.session.execute(
            select(OpenLoop).where(OpenLoop.project_id == project.id, OpenLoop.title.in_(titles))
        )
        existing_by_title = {item.title: item for item in existing.scalars()}
        loops: list[OpenLoop] = []
        for title in titles:
            loop = existing_by_title.get(title)
            if not loop:
                loop = OpenLoop(project_id=project.id, title=title[:240], description="Created during first-run intelligence.", status="open")
                self.session.add(loop)
                await self.session.flush()
            loops.append(loop)
        return loops

    async def _seed_first_run_understanding(
        self,
        user_id: UUID,
        *,
        current_mission: str,
        current_focus: str,
        goals: list[str],
        projects: list[Project],
        open_loops: list[OpenLoop],
        success_90_days: str,
        first_suggested_actions: list[str] | None = None,
        struggling_with: str | None = None,
        help_continue: str | None = None,
    ) -> None:
        suggested_actions = first_suggested_actions or [current_focus]
        entries = [
            ("current_mission", "Current Mission", current_mission, {"statement": current_mission}),
            ("current_focus", "Current Focus", current_focus, {"statement": current_focus}),
            ("goals", "Top Goals", "; ".join(goals[:5]), {"items": goals[:5]}),
            ("active_projects", "Active Projects", "; ".join(project.name for project in projects[:5]), {"items": [project.name for project in projects[:5]]}),
            ("open_loops", "Initial Open Loops", "; ".join(loop.title for loop in open_loops[:5]), {"items": [loop.title for loop in open_loops[:5]]}),
            ("success_metrics", "90-Day Success", success_90_days, {"statement": success_90_days}),
            ("next_suggested_actions", "Suggested First Actions", "; ".join(suggested_actions[:5]), {"items": suggested_actions[:5]}),
        ]
        if struggling_with:
            entries.append(("current_blockers", "Current Blockers", struggling_with, {"statement": struggling_with}))
        if help_continue:
            entries.append(("continuity_request", "What To Continue", help_continue, {"statement": help_continue}))
        for category, title, value, payload in entries:
            await self._upsert_understanding(user_id, category, title, value, payload)

    async def _upsert_understanding(self, user_id: UUID, category: str, title: str, value: str, payload: dict) -> None:
        result = await self.session.execute(
            select(UserUnderstanding).where(UserUnderstanding.user_id == user_id, UserUnderstanding.category == category, UserUnderstanding.title == title).limit(1)
        )
        item = result.scalar_one_or_none()
        if not item:
            item = UserUnderstanding(user_id=user_id, category=category, title=title[:120], value=value or title, source="user", confidence=1.0)
            self.session.add(item)
        item.value = truncate(value or title, 4000)
        if category == "current_mission":
            item.current_mission = payload
        elif category == "current_focus":
            item.current_focus = payload
        elif category == "active_projects":
            item.active_projects = payload
        elif category == "open_loops":
            item.open_loops = payload
        elif category == "goals":
            item.goals = payload
        elif category == "next_suggested_actions":
            item.next_suggested_actions = payload
        await self.session.flush()

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
