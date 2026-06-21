from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.conversation import Conversation
from app.models.note import Note
from app.models.open_loop_action import OpenLoopAction
from app.models.project import Project
from app.models.project_intelligence_phase2 import Decision, OpenLoop
from app.models.task import Task
from app.schemas.open_loops_engine import OpenLoopEngineItem, OpenLoopEngineOut, OpenLoopEngineSummary
from app.services.usage_event_service import UsageEventService


OPEN_TASK_STATUSES = {"todo", "pending", "in_progress"}
DONE_TASK_STATUSES = {"completed", "done", "archived"}
OPEN_LOOP_TYPES = {
    "waiting": "waiting_response",
    "follow": "follow_up",
    "block": "blocked_work",
    "stuck": "blocked_work",
    "decision": "pending_decision",
    "idea": "incomplete_idea",
}


class OpenLoopsEngineService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, user_id: UUID) -> OpenLoopEngineOut:
        projects = await self._projects(user_id)
        project_names = {str(project.id): project.name for project in projects}
        actions = await self._actions(user_id)
        tasks = await self._tasks(user_id)
        decisions = await self._decisions(user_id)
        loops = await self._loops(user_id)
        conversations = await self._conversations(user_id)
        notes = await self._notes(user_id)

        items = [
            *[self._task_item(task, project_names) for task in tasks if task.status not in DONE_TASK_STATUSES],
            *[self._decision_item(decision, project_names) for decision in decisions if decision.status == "pending"],
            *[self._loop_item(loop, project_names) for loop in loops if loop.status != "archived"],
            *[self._conversation_item(conversation, project_names) for conversation in conversations if conversation.active_intent],
            *[self._note_item(note, project_names) for note in notes if self._looks_like_incomplete_idea(note)],
        ]
        items = [self._apply_action(item, actions) for item in items]
        items = [item for item in items if item.status == "open"]
        items.sort(key=lambda item: (self._priority_rank(item.priority), item.updatedAt), reverse=True)
        return OpenLoopEngineOut(items=items, summary=self._summary(items))

    async def complete(self, user_id: UUID, source: str, source_id: UUID) -> OpenLoopEngineItem:
        item = await self._owned_source(user_id, source, source_id)
        if isinstance(item, Task):
            item.status = "completed"
        elif isinstance(item, Decision):
            item.status = "decided"
        elif isinstance(item, OpenLoop):
            item.status = "completed"
        elif isinstance(item, Conversation):
            item.active_intent = None
        elif isinstance(item, Note):
            tags = list(item.tags or [])
            if "open-loop-completed" not in tags:
                tags.append("open-loop-completed")
            item.tags = tags
        await self._set_action(user_id, source, source_id, "completed")
        await UsageEventService(self.session).track(
            user_id=user_id,
            event_type="open_loop_completed",
            surface="open_loops",
            metadata={"source": source, "source_id": str(source_id)},
        )
        await self.session.flush()
        return await self._single(user_id, source, source_id, "completed")

    async def snooze(self, user_id: UUID, source: str, source_id: UUID) -> OpenLoopEngineItem:
        item = await self._owned_source(user_id, source, source_id)
        if isinstance(item, Note):
            item.tags = self._tagged(item.tags, "open-loop-snoozed")
        await self._set_action(user_id, source, source_id, "snoozed")
        await self.session.flush()
        return await self._single(user_id, source, source_id, "snoozed")

    async def ignore(self, user_id: UUID, source: str, source_id: UUID) -> OpenLoopEngineItem:
        item = await self._owned_source(user_id, source, source_id)
        if isinstance(item, Note):
            item.tags = self._tagged(item.tags, "open-loop-ignored")
        await self._set_action(user_id, source, source_id, "ignored")
        await self.session.flush()
        return await self._single(user_id, source, source_id, "ignored")

    async def _actions(self, user_id: UUID) -> dict[str, str]:
        result = await self.session.execute(select(OpenLoopAction).where(OpenLoopAction.user_id == user_id))
        return {self._action_key(item.source, item.source_id): item.status for item in result.scalars()}

    async def _set_action(self, user_id: UUID, source: str, source_id: UUID, status: str) -> None:
        key = str(source_id)
        result = await self.session.execute(
            select(OpenLoopAction).where(
                OpenLoopAction.user_id == user_id,
                OpenLoopAction.source == source,
                OpenLoopAction.source_id == key,
            )
        )
        action = result.scalar_one_or_none()
        if action:
            action.status = status
            return
        self.session.add(OpenLoopAction(user_id=user_id, source=source, source_id=key, status=status))

    async def _projects(self, user_id: UUID) -> list[Project]:
        result = await self.session.execute(
            select(Project).where(Project.user_id == user_id, Project.deleted_at.is_(None)).order_by(Project.updated_at.desc())
        )
        return list(result.scalars())

    async def _tasks(self, user_id: UUID) -> list[Task]:
        result = await self.session.execute(
            select(Task).where(Task.user_id == user_id, Task.deleted_at.is_(None)).order_by(Task.updated_at.desc()).limit(80)
        )
        return list(result.scalars())

    async def _decisions(self, user_id: UUID) -> list[Decision]:
        result = await self.session.execute(
            select(Decision)
            .join(Project, Project.id == Decision.project_id)
            .where(Project.user_id == user_id, Project.deleted_at.is_(None))
            .order_by(Decision.updated_at.desc())
            .limit(80)
        )
        return list(result.scalars())

    async def _loops(self, user_id: UUID) -> list[OpenLoop]:
        result = await self.session.execute(
            select(OpenLoop)
            .join(Project, Project.id == OpenLoop.project_id)
            .where(Project.user_id == user_id, Project.deleted_at.is_(None))
            .order_by(OpenLoop.updated_at.desc())
            .limit(80)
        )
        return list(result.scalars())

    async def _conversations(self, user_id: UUID) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None), Conversation.archived_at.is_(None))
            .order_by(Conversation.updated_at.desc())
            .limit(40)
        )
        return list(result.scalars())

    async def _notes(self, user_id: UUID) -> list[Note]:
        result = await self.session.execute(
            select(Note).where(Note.user_id == user_id, Note.deleted_at.is_(None)).order_by(Note.updated_at.desc()).limit(40)
        )
        return list(result.scalars())

    async def _owned_source(self, user_id: UUID, source: str, source_id: UUID):
        if source == "task":
            result = await self.session.execute(select(Task).where(Task.id == source_id, Task.user_id == user_id, Task.deleted_at.is_(None)))
        elif source == "decision":
            result = await self.session.execute(
                select(Decision).join(Project, Project.id == Decision.project_id).where(Decision.id == source_id, Project.user_id == user_id, Project.deleted_at.is_(None))
            )
        elif source == "open_loop":
            result = await self.session.execute(
                select(OpenLoop).join(Project, Project.id == OpenLoop.project_id).where(OpenLoop.id == source_id, Project.user_id == user_id, Project.deleted_at.is_(None))
            )
        elif source == "conversation":
            result = await self.session.execute(select(Conversation).where(Conversation.id == source_id, Conversation.user_id == user_id, Conversation.deleted_at.is_(None)))
        elif source == "note":
            result = await self.session.execute(select(Note).where(Note.id == source_id, Note.user_id == user_id, Note.deleted_at.is_(None)))
        else:
            raise NotFoundError("Open loop source not found")
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("Open loop source not found")
        return item

    async def _single(self, user_id: UUID, source: str, source_id: UUID, status: str) -> OpenLoopEngineItem:
        project_names = {str(project.id): project.name for project in await self._projects(user_id)}
        item = await self._owned_source(user_id, source, source_id)
        if isinstance(item, Task):
            return self._task_item(item, project_names, status)
        if isinstance(item, Decision):
            return self._decision_item(item, project_names, status)
        if isinstance(item, OpenLoop):
            return self._loop_item(item, project_names, status)
        if isinstance(item, Conversation):
            return self._conversation_item(item, project_names, status)
        return self._note_item(item, project_names, status)

    def _task_item(self, task: Task, project_names: dict[str, str], status: str = "open") -> OpenLoopEngineItem:
        priority = self._priority(task.priority)
        loop_type = "blocked_work" if task.status == "blocked" else "unfinished_task"
        return self._item(
            id=f"task:{task.id}",
            source="task",
            source_id=task.id,
            title=task.title,
            description=task.description or self._task_detail(task),
            project_id=task.project_id,
            project_names=project_names,
            loop_type=loop_type,
            status=status,
            created_at=task.created_at,
            updated_at=task.updated_at,
            priority=priority,
            href="/tasks",
            next_step=f"Finish or clarify: {task.title}",
        )

    def _decision_item(self, decision: Decision, project_names: dict[str, str], status: str = "open") -> OpenLoopEngineItem:
        return self._item(
            id=f"decision:{decision.id}",
            source="decision",
            source_id=decision.id,
            title=decision.title,
            description=decision.description or "Pending decision.",
            project_id=decision.project_id,
            project_names=project_names,
            loop_type="pending_decision",
            status=status,
            created_at=decision.created_at,
            updated_at=decision.updated_at,
            priority="high",
            href=self._project_href(decision.project_id),
            next_step=f"Make or record the decision: {decision.title}",
        )

    def _loop_item(self, loop: OpenLoop, project_names: dict[str, str], status: str | None = None) -> OpenLoopEngineItem:
        loop_type = self._classify(loop.title, loop.description)
        return self._item(
            id=f"open_loop:{loop.id}",
            source="open_loop",
            source_id=loop.id,
            title=loop.title,
            description=loop.description or "Tracked unfinished work.",
            project_id=loop.project_id,
            project_names=project_names,
            loop_type=loop_type,
            status=status or ("completed" if loop.status == "completed" else "open"),
            created_at=loop.created_at,
            updated_at=loop.updated_at,
            priority="high" if loop_type in {"blocked_work", "pending_decision", "waiting_response"} else "medium",
            href=self._project_href(loop.project_id),
            next_step=f"Close the loop: {loop.title}",
        )

    def _conversation_item(self, conversation: Conversation, project_names: dict[str, str], status: str = "open") -> OpenLoopEngineItem:
        title = conversation.active_intent or conversation.title or "Follow up on conversation"
        return self._item(
            id=f"conversation:{conversation.id}",
            source="conversation",
            source_id=conversation.id,
            title=title,
            description=conversation.summary or "Conversation has an unresolved active intent.",
            project_id=conversation.project_id,
            project_names=project_names,
            loop_type="follow_up",
            status=status,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            priority="medium",
            href=f"/chat?conversation={conversation.id}",
            next_step=f"Follow up on: {title}",
        )

    def _note_item(self, note: Note, project_names: dict[str, str], status: str = "open") -> OpenLoopEngineItem:
        title = note.title or "Incomplete idea"
        return self._item(
            id=f"note:{note.id}",
            source="note",
            source_id=note.id,
            title=title,
            description=note.summary or note.content[:180],
            project_id=note.project_id,
            project_names=project_names,
            loop_type="incomplete_idea",
            status=status,
            created_at=note.created_at,
            updated_at=note.updated_at,
            priority="low",
            href="/notes",
            next_step=f"Turn this idea into a decision, task, or project note: {title}",
        )

    def _item(
        self,
        *,
        id: str,
        source: str,
        source_id: UUID,
        title: str,
        description: str,
        project_id: UUID | None,
        project_names: dict[str, str],
        loop_type: str,
        status: str,
        created_at: datetime,
        updated_at: datetime,
        priority: str,
        href: str,
        next_step: str,
    ) -> OpenLoopEngineItem:
        return OpenLoopEngineItem(
            id=id,
            source=source,
            sourceId=str(source_id),
            title=title,
            description=description,
            projectId=str(project_id) if project_id else None,
            projectName=project_names.get(str(project_id), "No project"),
            type=loop_type,
            status=status,
            createdAt=created_at,
            updatedAt=updated_at,
            priority=priority,
            href=href,
            nextStep=next_step,
        )

    @staticmethod
    def _summary(items: list[OpenLoopEngineItem]) -> OpenLoopEngineSummary:
        return OpenLoopEngineSummary(
            total=len(items),
            highPriority=sum(item.priority == "high" for item in items),
            pendingDecisions=sum(item.type == "pending_decision" for item in items),
            blockedWork=sum(item.type == "blocked_work" for item in items),
            followUps=sum(item.type == "follow_up" for item in items),
        )

    @staticmethod
    def _apply_action(item: OpenLoopEngineItem, actions: dict[str, str]) -> OpenLoopEngineItem:
        status = actions.get(OpenLoopsEngineService._action_key(item.source, item.sourceId))
        if status in {"completed", "snoozed", "ignored"}:
            item.status = status
        return item

    @staticmethod
    def _action_key(source: str, source_id: str) -> str:
        return f"{source}:{source_id}"

    @staticmethod
    def _classify(title: str, description: str) -> str:
        text = f"{title} {description}".casefold()
        for key, loop_type in OPEN_LOOP_TYPES.items():
            if key in text:
                return loop_type
        return "unfinished_task"

    @staticmethod
    def _looks_like_incomplete_idea(note: Note) -> bool:
        tags = set(note.tags or [])
        if tags.intersection({"open-loop-completed", "open-loop-ignored", "open-loop-snoozed"}):
            return False
        text = f"{note.title or ''} {note.summary or ''} {note.content}".casefold()
        return any(marker in text for marker in ("todo", "follow up", "unfinished", "idea:", "maybe", "need to", "pending", "blocked"))

    @staticmethod
    def _priority(value: str) -> str:
        return value if value in {"high", "medium", "low"} else "medium"

    @staticmethod
    def _priority_rank(value: str) -> int:
        return {"high": 3, "medium": 2, "low": 1}.get(value, 2)

    @staticmethod
    def _task_detail(task: Task) -> str:
        if task.due_at:
            return f"Due {task.due_at.date().isoformat()}."
        return f"Status: {task.status.replace('_', ' ')}."

    @staticmethod
    def _project_href(project_id: UUID | None) -> str:
        return f"/projects/{project_id}" if project_id else "/projects"

    @staticmethod
    def _tagged(tags, tag: str) -> list[str]:
        values = list(tags or [])
        if tag not in values:
            values.append(tag)
        return values
