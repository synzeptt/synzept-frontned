from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_brief_phase8 import DailyBriefSnapshot
from app.models.note import Note
from app.models.project import Project
from app.models.task import Task
from app.models.timeline_event import TimelineEvent
from app.services.context_engine_phase6_service import ContextEnginePhase6Service
from app.services.open_loops_engine_service import OpenLoopsEngineService


class DailyBriefPhase8Service:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def today(self, user_id: UUID) -> dict:
        today = date.today()
        result = await self.session.execute(
            select(DailyBriefSnapshot).where(DailyBriefSnapshot.user_id == user_id, DailyBriefSnapshot.brief_date == today)
        )
        brief = result.scalar_one_or_none()
        if brief:
            return self._brief_out(brief)
        return await self.refresh(user_id)

    async def refresh(self, user_id: UUID) -> dict:
        context = await ContextEnginePhase6Service(self.session).refresh(user_id)
        projects = await self._projects(user_id)
        tasks = await self._tasks(user_id)
        notes = await self._notes(user_id)
        timeline = await self._timeline(user_id)
        open_loop_engine = await OpenLoopsEngineService(self.session).list(user_id)
        today = date.today()
        result = await self.session.execute(
            select(DailyBriefSnapshot).where(DailyBriefSnapshot.user_id == user_id, DailyBriefSnapshot.brief_date == today)
        )
        brief = result.scalar_one_or_none()
        what_matters = self._what_matters(context, projects, tasks)
        open_loops = [self._engine_loop_item(item) for item in open_loop_engine.items if item.status == "open"] or self._open_loops(context, tasks)
        recent_progress = self._recent_progress(context, projects, tasks, notes, timeline)
        projects_needing_attention = self._projects_needing_attention(projects, context["openLoops"])
        recommended_next_step = self._recommended_next_step(context, what_matters, open_loops, projects_needing_attention)
        context_to_remember = self._context_to_remember(context, notes, timeline)
        values = {
            "context_snapshot_id": context["id"],
            "what_matters_today": what_matters[:6],
            "open_loops": open_loops[:6],
            "recommended_next_step": recommended_next_step,
            "recent_progress": recent_progress[:6],
            "context_to_remember": [*projects_needing_attention[:6], *context_to_remember[:6]],
        }
        if brief:
            for field, value in values.items():
                setattr(brief, field, value)
            brief.updated_at = datetime.now(timezone.utc)
        else:
            brief = DailyBriefSnapshot(user_id=user_id, brief_date=today, **values)
            self.session.add(brief)
        await self.session.flush()
        return self._brief_out(brief)

    async def _projects(self, user_id: UUID) -> list[Project]:
        result = await self.session.execute(
            select(Project)
            .where(Project.user_id == user_id, Project.deleted_at.is_(None), Project.status.in_(["active", "paused"]))
            .order_by(Project.updated_at.desc())
            .limit(12)
        )
        return list(result.scalars())

    async def _tasks(self, user_id: UUID) -> list[Task]:
        result = await self.session.execute(
            select(Task)
            .where(Task.user_id == user_id, Task.deleted_at.is_(None))
            .order_by(Task.updated_at.desc())
            .limit(30)
        )
        return list(result.scalars())

    async def _notes(self, user_id: UUID) -> list[Note]:
        result = await self.session.execute(
            select(Note)
            .where(Note.user_id == user_id, Note.deleted_at.is_(None))
            .order_by(Note.updated_at.desc())
            .limit(12)
        )
        return list(result.scalars())

    async def _timeline(self, user_id: UUID) -> list[TimelineEvent]:
        result = await self.session.execute(
            select(TimelineEvent)
            .where(TimelineEvent.user_id == user_id)
            .order_by(TimelineEvent.event_date.desc(), TimelineEvent.created_at.desc())
            .limit(12)
        )
        return list(result.scalars())

    def _what_matters(self, context: dict, projects: list[Project], tasks: list[Task]) -> list[dict]:
        items: list[dict] = []
        current_focus = context["currentFocus"]
        if current_focus.get("title"):
            items.append(
                self._item(
                    "current_focus",
                    current_focus.get("title", "Current focus"),
                    current_focus.get("detail") or "Most visible workspace focus.",
                    href=self._project_href(current_focus.get("projectId")),
                    priority="high",
                    source="context",
                )
            )

        for task in self._priority_tasks(tasks):
            detail = self._task_detail(task)
            items.append(self._item("task", task.title, detail, href="/tasks", priority=task.priority, source="tasks"))

        for project in projects[:4]:
            title = project.current_focus or project.recommended_next_step or project.name
            detail = project.name if title != project.name else project.description or "Active project."
            items.append(self._item("project", title, detail, href=self._project_href(project.id), priority="medium", source="projects"))

        for theme in context["activeThemes"][:4]:
            items.append(self._item(theme.get("type", "theme"), theme.get("title", "Workspace theme"), theme.get("detail", ""), source="context"))

        return self._unique_items(items)

    def _open_loops(self, context: dict, tasks: list[Task]) -> list[dict]:
        items: list[dict] = []
        for loop in context["openLoops"]:
            title = loop.get("title") or loop.get("description") or "Open loop"
            detail = loop.get("description") or loop.get("projectName") or "Unfinished work."
            items.append(
                self._item(
                    "open_loop",
                    title,
                    detail,
                    href=self._project_href(loop.get("projectId")),
                    priority="high",
                    source="project_intelligence",
                )
            )

        for task in tasks:
            if task.status in {"completed", "done", "archived"}:
                continue
            items.append(self._item("pending_task", task.title, self._task_detail(task), href="/tasks", priority=task.priority, source="tasks"))

        return self._unique_items(items)

    @staticmethod
    def _engine_loop_item(item) -> dict:
        return {
            "type": item.type,
            "title": item.title,
            "detail": item.description or item.nextStep,
            "href": item.href,
            "priority": item.priority,
            "source": "open_loops_engine",
            "projectName": item.projectName,
        }

    def _recent_progress(
        self,
        context: dict,
        projects: list[Project],
        tasks: list[Task],
        notes: list[Note],
        timeline: list[TimelineEvent],
    ) -> list[dict]:
        items: list[dict] = []
        for event in timeline:
            if event.event_type in {"progress", "achievement", "milestone", "decision"}:
                items.append(
                    self._item(
                        f"timeline_{event.event_type}",
                        event.title,
                        event.description,
                        href="/timeline",
                        priority="medium" if event.importance < 0.75 else "high",
                        source="timeline",
                    )
                )
        for task in tasks:
            if task.status in {"completed", "done"}:
                items.append(self._item("completed_task", task.title, "Completed work.", href="/tasks", source="tasks"))
        for project in projects[:4]:
            items.append(self._item("project_update", project.name, project.current_focus or "Project updated recently.", href=self._project_href(project.id), source="projects"))
        for note in notes[:4]:
            items.append(self._item("note", note.title or "Recent note", note.summary or note.content[:140], href="/notes", source="notes"))
        for theme in context["activeThemes"]:
            if str(theme.get("type", "")).startswith("timeline_"):
                items.append(self._item(theme.get("type", "timeline"), theme.get("title", "Recent progress"), theme.get("detail", ""), href="/timeline", source="timeline"))
        return self._unique_items(items)

    def _projects_needing_attention(self, projects: list[Project], open_loops: list[dict]) -> list[dict]:
        loop_counts: dict[str, int] = {}
        for loop in open_loops:
            project_id = loop.get("projectId")
            if project_id:
                loop_counts[str(project_id)] = loop_counts.get(str(project_id), 0) + 1

        items: list[dict] = []
        stale_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        for project in projects:
            reasons: list[str] = []
            updated_at = self._aware(project.updated_at)
            if not project.current_focus.strip():
                reasons.append("No current focus")
            if not project.recommended_next_step.strip():
                reasons.append("No recommended next step")
            if loop_counts.get(str(project.id)):
                reasons.append(f"{loop_counts[str(project.id)]} open loop{'s' if loop_counts[str(project.id)] != 1 else ''}")
            if updated_at and updated_at < stale_cutoff:
                reasons.append("No recent activity")
            if project.status == "paused":
                reasons.append("Paused project")
            if reasons:
                items.append(
                    self._item(
                        "project_attention",
                        project.name,
                        ", ".join(reasons[:3]),
                        href=self._project_href(project.id),
                        priority="high" if loop_counts.get(str(project.id)) or not project.recommended_next_step.strip() else "medium",
                        source="projects",
                    )
                )
        return items[:6]

    def _recommended_next_step(
        self,
        context: dict,
        what_matters: list[dict],
        open_loops: list[dict],
        projects_needing_attention: list[dict],
    ) -> dict:
        current = context["recommendedNextStep"] or {}
        if current.get("title"):
            return self._item(
                current.get("source", "recommendation"),
                current.get("title", "Recommended next step"),
                current.get("reason", "This is the clearest continuation point."),
                href=self._project_href(current.get("projectId")),
                priority="high",
                source="context",
            )
        if open_loops:
            loop = open_loops[0]
            return self._item("open_loop", loop["title"], f"Resolve this unfinished loop: {loop.get('detail', '')}", href=loop.get("href") or "/tasks", priority="high", source="open_loops")
        if projects_needing_attention:
            project = projects_needing_attention[0]
            return self._item("project_attention", project["title"], f"Give this project a clear focus: {project.get('detail', '')}", href=project.get("href") or "/projects", priority="high", source="projects")
        if what_matters:
            item = what_matters[0]
            return self._item("priority", item["title"], "Start with the highest visible priority.", href=item.get("href") or "/dashboard", priority="high", source="priorities")
        return self._item("empty_state", "Choose one meaningful priority for today.", "A clear next action gives Synzept a useful return point.", href="/projects", priority="medium", source="empty_state")

    def _context_to_remember(self, context: dict, notes: list[Note], timeline: list[TimelineEvent]) -> list[dict]:
        items: list[dict] = []
        for item in context["importantContext"]:
            items.append(self._item(item.get("type", "context"), item.get("title", "Context"), item.get("detail", ""), source="memory"))
        for event in timeline:
            if event.event_type == "decision":
                items.append(self._item("decision", event.title, event.description, href="/timeline", priority="high", source="timeline"))
        for note in notes[:4]:
            items.append(self._item("note", note.title or "Recent note", note.summary or note.content[:140], href="/notes", source="notes"))
        return self._unique_items(items)

    def _priority_tasks(self, tasks: list[Task]) -> list[Task]:
        open_tasks = [task for task in tasks if task.status not in {"completed", "done", "archived"}]
        return sorted(open_tasks, key=lambda task: (0 if task.due_at else 1, self._priority_rank(task.priority), self._aware(task.due_at) or datetime.max.replace(tzinfo=timezone.utc)))[:6]

    @staticmethod
    def _priority_rank(priority: str) -> int:
        return {"high": 0, "medium": 1, "low": 2}.get(priority, 1)

    @staticmethod
    def _task_detail(task: Task) -> str:
        if task.due_at:
            due = task.due_at.date().isoformat()
            return f"Due {due}. Priority: {task.priority}."
        return f"Priority: {task.priority}. Status: {task.status}."

    @staticmethod
    def _project_href(project_id) -> str | None:
        return f"/projects/{project_id}" if project_id else None

    @staticmethod
    def _aware(value: datetime | None) -> datetime | None:
        if not value:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @staticmethod
    def _item(item_type: str, title: str, detail: str | None = "", *, href: str | None = None, priority: str = "medium", source: str = "workspace") -> dict:
        return {
            "type": item_type,
            "title": str(title or "").strip(),
            "detail": str(detail or "").strip(),
            "href": href,
            "priority": priority,
            "source": source,
        }

    @staticmethod
    def _unique_items(items: list[dict]) -> list[dict]:
        seen: set[str] = set()
        result: list[dict] = []
        for item in items:
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            key = title.casefold()
            if key in seen:
                continue
            seen.add(key)
            item["title"] = title
            result.append(item)
        return result

    def _brief_out(self, brief: DailyBriefSnapshot) -> dict:
        now = datetime.now(timezone.utc)
        context_to_remember = brief.context_to_remember or []
        return {
            "id": brief.id,
            "userId": brief.user_id,
            "contextSnapshotId": brief.context_snapshot_id,
            "briefDate": brief.brief_date,
            "whatMattersToday": brief.what_matters_today or [],
            "openLoops": brief.open_loops or [],
            "recommendedNextStep": brief.recommended_next_step or {},
            "recentProgress": brief.recent_progress or [],
            "projectsNeedingAttention": self._extract_projects_needing_attention(context_to_remember),
            "contextToRemember": self._remove_projects_needing_attention(context_to_remember),
            "createdAt": brief.created_at or now,
            "updatedAt": brief.updated_at or brief.created_at or now,
        }

    @staticmethod
    def _extract_projects_needing_attention(context_to_remember: list) -> list[dict]:
        return [item for item in context_to_remember if isinstance(item, dict) and item.get("type") == "project_attention"]

    @staticmethod
    def _remove_projects_needing_attention(context_to_remember: list) -> list[dict]:
        return [item for item in context_to_remember if not (isinstance(item, dict) and item.get("type") == "project_attention")]
