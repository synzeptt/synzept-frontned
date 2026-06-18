from app.models.user import User
from app.schemas.continuity_mode import ContinuityActionOut, ContinuityModeOut
from app.services.continuity_assistant_service import ContinuityAssistantService
from app.utils.text import truncate


class ContinuityModeService:
    def __init__(self, session) -> None:
        self.session = session
        self.assistant = ContinuityAssistantService(session)

    async def snapshot(self, user: User) -> ContinuityModeOut:
        context = await self.assistant._context(user.id)
        priorities = self.assistant._priorities(context)
        open_loops = self.assistant._open_loops(context)
        recent_progress = self.assistant._recent_progress(context)
        key_context = self.assistant._key_context(context)
        recommendation = self.assistant._recommendation(context)
        projects = [project for project in context["projects"] if project.status == "active"]
        goals = [goal for goal in context["goals"] if goal.status == "active"]
        recent_project = projects[0] if projects else None

        last_focus = self._last_focus(context, priorities, recent_project)
        return ContinuityModeOut(
            headline=f"Welcome back{', ' + user.display_name if user.display_name else ''}.",
            last_focus=last_focus,
            what_changed=self._fallback_list(
                recent_progress,
                fallback="No major changes were recorded since your last visit.",
                limit=5,
            ),
            open_loops=self._fallback_list(
                open_loops,
                fallback="Tell Synzept what still feels unfinished.",
                limit=5,
            ),
            recommended_next_action=recommendation.title,
            recommended_reason=recommendation.reason or recommendation.detail,
            actions=self._actions(
                recent_project_name=recent_project.name if recent_project else None,
                recent_project_id=str(recent_project.id) if recent_project else None,
                top_goal=goals[0].title if goals else None,
                learning_context=key_context[0] if key_context else None,
            ),
            memory_context=[truncate(item, 180) for item in key_context[:5]],
            context_used={
                "memories": len(context["memories"]),
                "projects": len(context["projects"]),
                "goals": len(context["goals"]),
                "open_loops": len(open_loops),
                "understanding": len(context["understanding"]),
                "recent_activity": len(context["activities"]) + len(context["conversations"]),
            },
        )

    @staticmethod
    def _last_focus(context: dict, priorities: list[str], recent_project) -> str:
        conversation = next((item for item in context["conversations"] if item.active_intent or item.title), None)
        if conversation and conversation.active_intent:
            return conversation.active_intent
        if recent_project:
            return recent_project.current_focus or recent_project.recommended_next_step or recent_project.name
        if priorities:
            return priorities[0]
        if conversation:
            return conversation.title or "A recent conversation"
        return "Your current work is ready to continue."

    @staticmethod
    def _fallback_list(items: list[str], *, fallback: str, limit: int) -> list[str]:
        return items[:limit] if items else [fallback]

    @staticmethod
    def _actions(
        *,
        recent_project_name: str | None,
        recent_project_id: str | None,
        top_goal: str | None,
        learning_context: str | None,
    ) -> list[ContinuityActionOut]:
        recent_project = recent_project_name or "my recent project"
        goal = top_goal or "my personal goals"
        learning = learning_context or "what I have been learning"
        return [
            ContinuityActionOut(
                label="Continue Startup",
                mode="startup",
                prompt="Help me continue my startup work. Use my current mission, recent progress, open loops, projects, and memory before recommending the next step.",
            ),
            ContinuityActionOut(
                label="Continue Personal Goals",
                mode="personal_goals",
                prompt=f"Help me continue {goal}. Use my goals, open loops, recent activity, and user understanding before suggesting the next action.",
            ),
            ContinuityActionOut(
                label="Continue Learning",
                mode="learning",
                prompt=f"Help me continue learning from {learning}. Connect this to my recent work, memories, and unfinished questions.",
            ),
            ContinuityActionOut(
                label="Continue Recent Project",
                mode="recent_project",
                project_id=recent_project_id,
                prompt=f"Help me continue {recent_project}. Restore the project context, summarize what changed, identify open loops, and recommend the next action.",
            ),
        ]
