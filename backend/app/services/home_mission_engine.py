from app.services.home_context import HomeContext
from app.utils.text import truncate


class MissionEngine:
    EMPTY = "Add a mission in Synzept Knows You so Home can hold your north star."

    def generate(self, context: HomeContext) -> str:
        return (
            self._first(context.profile.current_mission)
            or self._understanding(context, ("current_mission", "missions", "long_term_goals", "short_term_goals"))
            or self._memory(context, ("goals", "long_term_plans"))
            or self._project_mission(context)
            or self.EMPTY
        )

    @staticmethod
    def _first(values: list[str]) -> str:
        return truncate(values[0], 260) if values else ""

    @staticmethod
    def _understanding(context: HomeContext, categories: tuple[str, ...]) -> str:
        for item in context.understanding:
            if item.category in categories and item.value.strip():
                return truncate(item.value, 260)
        return ""

    @staticmethod
    def _memory(context: HomeContext, memory_types: tuple[str, ...]) -> str:
        for memory in context.memories:
            if memory.memory_type in memory_types:
                return truncate(memory.summary or memory.content, 260)
        return ""

    @staticmethod
    def _project_mission(context: HomeContext) -> str:
        project = next((item for item in context.projects if item.description), None)
        if project:
            return truncate(project.description or project.name, 260)
        if context.projects:
            return f"Keep momentum on {context.projects[0].name}."
        return ""
