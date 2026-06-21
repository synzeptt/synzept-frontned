from app.schemas.home import HomeActionOut, HomeContinueContextOut, HomeSignalOut
from app.services.home_context import HomeContext
from app.utils.text import truncate


class ContinueContextEngine:
    def generate(self, context: HomeContext, *, mission: str, focus: str, open_loops: list[HomeSignalOut], action: HomeActionOut) -> HomeContinueContextOut:
        cards = self._cards(context, open_loops, action)
        prompt = "\n".join(
            [
                "Continue working from Synzept Home.",
                "",
                f"Mission: {mission}",
                f"Current Focus: {focus}",
                "Open Loops: " + ("; ".join(item.title for item in open_loops) or "None visible"),
                f"Suggested Next Action: {action.title}",
                action.reason and f"Why: {action.reason}",
                "",
                "Do not ask me to re-explain. Restore the context and help me take the next concrete step.",
            ]
        )
        return HomeContinueContextOut(
            title="Continue Working",
            summary=self._summary(context, action),
            prompt=prompt,
            cards=cards,
            sources={
                "user_understanding": len(context.understanding),
                "memory": len(context.memories),
                "projects": len(context.projects),
                "previous_conversations": len(context.conversations),
                "daily_activity": len(context.daily_summaries) + (1 if context.daily_brief else 0),
                "decisions": len(context.project_decisions) + len(context.decisions),
            },
        )

    @staticmethod
    def _cards(context: HomeContext, open_loops: list[HomeSignalOut], action: HomeActionOut) -> list[HomeSignalOut]:
        cards: list[HomeSignalOut] = []
        cards.append(HomeSignalOut(id="suggested-action", title=action.title, detail=action.reason, href=action.href, source=action.source, priority="high"))
        if open_loops:
            cards.append(open_loops[0])
        project = context.projects[0] if context.projects else None
        if project:
            cards.append(HomeSignalOut(id=str(project.id), title=project.name, detail=project.current_focus or project.recommended_next_step or project.description or "Active project", href=f"/projects/{project.id}", source="project"))
        conversation = context.conversations[0] if context.conversations else None
        if conversation:
            cards.append(HomeSignalOut(id=str(conversation.id), title=conversation.title or "Recent conversation", detail=truncate(conversation.summary or conversation.active_intent or "", 200), href=f"/chat?conversation={conversation.id}", source="previous_conversation"))
        return ContinueContextEngine._unique(cards)[:4]

    @staticmethod
    def _summary(context: HomeContext, action: HomeActionOut) -> str:
        if context.conversations:
            return f"Last thread and workspace context are ready. Start with: {action.title}"
        if context.projects or context.tasks:
            return f"Active work is ready to resume. Start with: {action.title}"
        return "Start with one mission, project, or task so Synzept can preserve continuity."

    @staticmethod
    def _unique(items: list[HomeSignalOut]) -> list[HomeSignalOut]:
        seen: set[str] = set()
        output: list[HomeSignalOut] = []
        for item in items:
            key = item.title.casefold()
            if key in seen:
                continue
            seen.add(key)
            output.append(item)
        return output
