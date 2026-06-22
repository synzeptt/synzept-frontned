from app.schemas.home import HomeSignalOut
from app.services.home_context import HomeContext
from app.utils.text import truncate


class OpenLoopEngine:
    def generate(self, context: HomeContext, *, limit: int = 5) -> list[HomeSignalOut]:
        loops: list[HomeSignalOut] = []
        loops.extend(
            HomeSignalOut(id=f"understanding-{index}", title=item, detail="Saved in User Understanding", href="/knows-you", source="knows_you", priority="high")
            for index, item in enumerate(context.profile.open_loops[:3])
        )
        loops.extend(
            HomeSignalOut(id=str(task.id), title=task.title, detail=task.description or "Open task", href="/tasks", source="task", priority=task.priority or "medium")
            for task in context.tasks
        )
        loops.extend(
            HomeSignalOut(id=str(loop.id), title=loop.loop, detail=f"Project loop in {project_name}", href=f"/projects/{loop.project_id}", source="project_open_loop", priority="high")
            for loop, project_name in context.project_open_loops
        )
        loops.extend(
            HomeSignalOut(id=str(decision.id), title=decision.decision, detail=f"Open decision in {project_name}", href=f"/projects/{decision.project_id}", source="decision", priority="high")
            for decision, project_name in context.project_decisions
        )
        loops.extend(
            HomeSignalOut(id=str(decision.id), title=decision.title, detail=decision.description or f"Decision in {project_name}", href=f"/projects/{decision.project_id}", source="decision", priority="high" if decision.status == "pending" else "medium")
            for decision, project_name in context.decisions
            if decision.status == "pending"
        )
        if context.daily_brief:
            loops.extend(self._daily_loops(context.daily_brief.open_loops))
        for summary in context.daily_summaries:
            loops.extend(
                HomeSignalOut(id=str(summary.id), title=truncate(str(item), 180), detail="Carried from daily activity", href="/daily-brief", source="daily_activity", priority="medium")
                for item in summary.unfinished_priorities[:3]
            )
        return self._unique(loops)[:limit]

    @staticmethod
    def _daily_loops(items: list) -> list[HomeSignalOut]:
        loops: list[HomeSignalOut] = []
        for index, item in enumerate(items[:5]):
            if isinstance(item, dict):
                title = str(item.get("title") or item.get("loop") or item.get("summary") or item)
                detail = str(item.get("detail") or item.get("nextStep") or item.get("description") or "From Daily Brief")
            else:
                title = str(item)
                detail = "From Daily Brief"
            loops.append(HomeSignalOut(id=f"daily-{index}", title=truncate(title, 180), detail=truncate(detail, 220), href="/daily-brief", source="daily_activity", priority="medium"))
        return loops

    @staticmethod
    def _unique(items: list[HomeSignalOut]) -> list[HomeSignalOut]:
        seen: set[str] = set()
        output: list[HomeSignalOut] = []
        for item in items:
            key = item.title.casefold().strip()
            if not key or key in seen:
                continue
            seen.add(key)
            output.append(item)
        output.sort(key=lambda item: {"high": 3, "medium": 2, "low": 1}.get(item.priority, 2), reverse=True)
        return output
