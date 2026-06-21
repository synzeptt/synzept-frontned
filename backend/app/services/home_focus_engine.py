from app.services.home_context import HomeContext
from app.utils.text import truncate


class FocusEngine:
    EMPTY = "Choose the one thing that matters most right now."

    def generate(self, context: HomeContext) -> str:
        active_project = next((project for project in context.projects if project.current_focus), None)
        daily_focus = self._daily_focus(context)
        return (
            self._first(context.profile.current_focus)
            or self._understanding(context, ("current_focus", "priorities"))
            or daily_focus
            or (truncate(active_project.current_focus, 240) if active_project else "")
            or self._task_focus(context)
            or self._conversation_focus(context)
            or self.EMPTY
        )

    @staticmethod
    def _first(values: list[str]) -> str:
        return truncate(values[0], 240) if values else ""

    @staticmethod
    def _understanding(context: HomeContext, categories: tuple[str, ...]) -> str:
        for item in context.understanding:
            if item.category in categories and item.value.strip():
                return truncate(item.value, 240)
        return ""

    @staticmethod
    def _daily_focus(context: HomeContext) -> str:
        if context.daily_brief and context.daily_brief.what_matters_today:
            item = context.daily_brief.what_matters_today[0]
            if isinstance(item, dict):
                return truncate(str(item.get("title") or item.get("summary") or item), 240)
            return truncate(str(item), 240)
        for summary in context.daily_summaries:
            if summary.unfinished_priorities:
                return truncate(str(summary.unfinished_priorities[0]), 240)
        return ""

    @staticmethod
    def _task_focus(context: HomeContext) -> str:
        ranked = sorted(context.tasks, key=lambda task: ({"high": 3, "medium": 2, "low": 1}.get(task.priority or "medium", 2), task.updated_at), reverse=True)
        return ranked[0].title if ranked else ""

    @staticmethod
    def _conversation_focus(context: HomeContext) -> str:
        conversation = next((item for item in context.conversations if item.active_intent or item.summary), None)
        return truncate((conversation.active_intent or conversation.summary or conversation.title), 240) if conversation else ""
