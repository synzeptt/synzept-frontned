from app.schemas.home import HomeActionOut, HomeSignalOut
from app.services.home_context import HomeContext
from app.utils.text import truncate


class RecommendationEngine:
    EMPTY = HomeActionOut(
        title="Capture one priority for today.",
        reason="Synzept needs one active anchor to preserve continuity.",
        href="/chat",
    )

    def generate(self, context: HomeContext, *, focus: str, open_loops: list[HomeSignalOut]) -> HomeActionOut:
        learned = self._learned_action(context)
        if learned:
            return HomeActionOut(title=learned, reason="Generated from User Understanding.", href="/knows-you", source="user_understanding")
        if context.daily_brief and context.daily_brief.recommended_next_step:
            item = context.daily_brief.recommended_next_step
            title = str(item.get("title") or item.get("action") or item.get("summary") or "")
            if title:
                return HomeActionOut(title=truncate(title, 220), reason=str(item.get("reason") or "Recommended by Daily Brief."), href="/daily-brief", source="daily_activity")
        high_loop = next((item for item in open_loops if item.priority == "high"), None)
        if high_loop:
            return HomeActionOut(title=high_loop.title, reason=high_loop.detail or "This unfinished loop is highest priority.", href=high_loop.href or "/open-loops", source=high_loop.source)
        project = next((item for item in context.projects if item.recommended_next_step), None)
        if project:
            return HomeActionOut(title=truncate(project.recommended_next_step, 220), reason=f"{project.name} is active.", href=f"/projects/{project.id}", source="project")
        task = next((item for item in context.tasks if item.priority == "high"), None) or (context.tasks[0] if context.tasks else None)
        if task:
            return HomeActionOut(title=task.title, reason=task.description or "This is the clearest task to resume.", href="/tasks", source="task")
        if focus and not focus.startswith("Choose the one thing"):
            return HomeActionOut(title=focus, reason="Continue the current focus.", href="/chat", source="focus_engine")
        return self.EMPTY

    @staticmethod
    def _learned_action(context: HomeContext) -> str:
        if context.profile.next_suggested_actions:
            return truncate(context.profile.next_suggested_actions[0], 220)
        for item in context.understanding:
            if item.category == "next_suggested_actions" and item.value.strip():
                return truncate(item.value, 220)
        return ""
