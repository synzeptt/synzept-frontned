"""Continuity restoration cards for the daily dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.memory import Memory
from app.models.note import Note
from app.models.project import Project
from app.models.task import Task
from app.schemas.dashboard import ContinuityCardOut
from app.tasks.service import OPEN_STATUSES
from app.utils.text import tokenize, truncate


PRIORITY_WEIGHT = {"high": 1.0, "medium": 0.65, "low": 0.35}
MEMORY_TYPES_WITH_CONTINUITY_VALUE = {"goals", "projects", "project", "preferences", "work", "priority", "priorities"}


@dataclass(slots=True)
class ContinuityCandidate:
    kind: str
    title: str
    description: str
    href: str
    action_label: str
    updated_at: datetime | None
    priority: str = "medium"
    project_id: UUID | None = None
    task_id: UUID | None = None
    conversation_id: UUID | None = None
    note_id: UUID | None = None
    due_at: datetime | None = None
    unfinished_score: float = 0.0
    activity_score: float = 0.0
    relevance_score: float = 0.0
    memory_score: float = 0.0
    reason: str = ""
    continuation_prompt: str = ""


class ContinuityRestorationService:
    def __init__(self, session: AsyncSession | None) -> None:
        self.session = session

    def build_cards(
        self,
        *,
        projects: list[Project],
        conversations: list[Conversation],
        tasks: list[Task],
        notes: list[Note] | None = None,
        memories: list[Memory] | None = None,
    ) -> list[ContinuityCardOut]:
        notes = notes or []
        memories = memories or []
        project_activity = self._project_activity(projects, conversations, tasks, notes)
        memory_topics = self._memory_topics(memories)

        candidates: list[ContinuityCandidate] = []
        candidates.extend(self._task_candidates(tasks, project_activity, memory_topics))
        candidates.extend(self._conversation_candidates(conversations, project_activity, memory_topics))
        candidates.extend(self._project_candidates(projects, tasks, conversations, project_activity, memory_topics))
        candidates.extend(self._note_candidates(notes, project_activity, memory_topics))

        scored = [(candidate, self._score(candidate)) for candidate in candidates]
        scored.sort(key=lambda item: item[1], reverse=True)

        cards: list[ContinuityCardOut] = []
        seen: set[tuple[str, UUID | None]] = set()
        for candidate, score in scored:
            key = (candidate.kind, candidate.task_id or candidate.conversation_id or candidate.project_id or candidate.note_id)
            if key in seen:
                continue
            seen.add(key)
            cards.append(self._card(candidate, score))
            if len(cards) == 6:
                break
        return cards

    def rank_memories_for_dashboard(self, memories: list[Memory], *, query: str = "goals priorities projects preferences ongoing work") -> list[Memory]:
        query_tokens = tokenize(query)

        def score(memory: Memory) -> float:
            lexical = len(query_tokens & tokenize(f"{memory.memory_type} {memory.category or ''} {memory.summary or ''} {memory.content}")) / max(len(query_tokens), 1)
            type_boost = 0.18 if (memory.memory_type or memory.category or "").lower() in MEMORY_TYPES_WITH_CONTINUITY_VALUE else 0.0
            recency = self._recency_score(memory.updated_at or memory.created_at)
            importance = min(max(memory.importance_score, 0.0), 1.0)
            access = min(memory.retrieval_count * 0.015, 0.08)
            return importance * 0.42 + recency * 0.22 + lexical * 0.2 + type_boost + access

        ranked = sorted(memories, key=score, reverse=True)
        return ranked[:8]

    def _task_candidates(
        self,
        tasks: list[Task],
        project_activity: dict[UUID, float],
        memory_topics: set[str],
    ) -> list[ContinuityCandidate]:
        open_tasks = [task for task in tasks if task.status in OPEN_STATUSES]
        candidates: list[ContinuityCandidate] = []
        for task in open_tasks:
            title = task.title
            detail = task.description or self._task_status_summary(task)
            candidates.append(
                ContinuityCandidate(
                    kind="task",
                    title=title,
                    description=truncate(detail, 150),
                    action_label="Continue task",
                    href="/tasks",
                    project_id=task.project_id,
                    task_id=task.id,
                    priority=task.priority or "medium",
                    updated_at=task.updated_at,
                    due_at=task.due_at,
                    unfinished_score=1.0 if task.status == "in_progress" else 0.82,
                    activity_score=project_activity.get(task.project_id, 0.0) if task.project_id else 0.0,
                    relevance_score=self._topic_overlap(title, detail, memory_topics),
                    reason=self._task_reason(task),
                    continuation_prompt=f"Continue {title}?",
                )
            )
        return candidates

    def _conversation_candidates(
        self,
        conversations: list[Conversation],
        project_activity: dict[UUID, float],
        memory_topics: set[str],
    ) -> list[ContinuityCandidate]:
        candidates: list[ContinuityCandidate] = []
        for conversation in conversations:
            if conversation.archived_at is not None:
                continue
            text = conversation.summary or conversation.active_intent or "A recent discussion is ready to continue."
            candidates.append(
                ContinuityCandidate(
                    kind="conversation",
                    title=conversation.title or "Untitled conversation",
                    description=truncate(text, 150),
                    action_label="Resume thread",
                    href=f"/chat?conversation={conversation.id}",
                    project_id=conversation.project_id,
                    conversation_id=conversation.id,
                    priority="medium",
                    updated_at=conversation.updated_at,
                    unfinished_score=0.84 if conversation.active_intent else 0.5,
                    activity_score=project_activity.get(conversation.project_id, 0.0) if conversation.project_id else 0.35,
                    relevance_score=self._topic_overlap(conversation.title or "", text, memory_topics),
                    reason="Open thread with resumable context." if conversation.active_intent else "Recent discussion with resumable context.",
                    continuation_prompt=f"Resume {conversation.title or 'the recent discussion'}?",
                )
            )
        return candidates

    def _project_candidates(
        self,
        projects: list[Project],
        tasks: list[Task],
        conversations: list[Conversation],
        project_activity: dict[UUID, float],
        memory_topics: set[str],
    ) -> list[ContinuityCandidate]:
        open_counts = self._count_by_project([task for task in tasks if task.status in OPEN_STATUSES])
        thread_counts = self._count_by_project([conversation for conversation in conversations if conversation.archived_at is None])
        candidates: list[ContinuityCandidate] = []
        for project in projects:
            if project.status != "active":
                continue
            open_count = open_counts.get(project.id, 0)
            thread_count = thread_counts.get(project.id, 0)
            detail = project.context_summary or project.description or (
                f"{open_count} open task{'s' if open_count != 1 else ''}; "
                f"{thread_count} recent thread{'s' if thread_count != 1 else ''}."
            )
            candidates.append(
                ContinuityCandidate(
                    kind="project",
                    title=project.name,
                    description=truncate(detail, 150),
                    action_label="Open project",
                    href=f"/projects/{project.id}",
                    project_id=project.id,
                    priority="high" if open_count else "medium",
                    updated_at=project.updated_at,
                    unfinished_score=min(open_count * 0.24 + thread_count * 0.12, 1.0),
                    activity_score=project_activity.get(project.id, 0.0),
                    relevance_score=self._topic_overlap(project.name, detail, memory_topics),
                    reason=self._project_reason(open_count, thread_count),
                    continuation_prompt=f"Resume {project.name}?",
                )
            )
        return candidates

    def _note_candidates(
        self,
        notes: list[Note],
        project_activity: dict[UUID, float],
        memory_topics: set[str],
    ) -> list[ContinuityCandidate]:
        candidates: list[ContinuityCandidate] = []
        for note in notes[:8]:
            title = note.title or "Recent note"
            detail = note.summary or note.content
            candidates.append(
                ContinuityCandidate(
                    kind="note",
                    title=title,
                    description=truncate(detail, 140),
                    action_label="Review note",
                    href="/notes",
                    project_id=note.project_id,
                    note_id=note.id,
                    priority="low",
                    updated_at=note.updated_at,
                    unfinished_score=0.25,
                    activity_score=project_activity.get(note.project_id, 0.0) if note.project_id else 0.15,
                    relevance_score=self._topic_overlap(title, detail, memory_topics),
                    reason="Recent captured context.",
                    continuation_prompt=f"Turn {title} into next steps?",
                )
            )
        return candidates

    def _score(self, candidate: ContinuityCandidate) -> float:
        recency = self._recency_score(candidate.updated_at)
        priority = PRIORITY_WEIGHT.get(candidate.priority or "medium", 0.55)
        due_pressure = self._due_pressure(candidate.due_at)
        return round(
            candidate.unfinished_score * 0.34
            + recency * 0.2
            + priority * 0.16
            + candidate.activity_score * 0.12
            + candidate.relevance_score * 0.1
            + candidate.memory_score * 0.04
            + due_pressure * 0.04,
            4,
        )

    def _card(self, candidate: ContinuityCandidate, score: float) -> ContinuityCardOut:
        return ContinuityCardOut(
            id=f"{candidate.kind}:{candidate.task_id or candidate.conversation_id or candidate.project_id or candidate.note_id}",
            type=candidate.kind,
            title=candidate.title,
            description=candidate.description,
            action_label=candidate.action_label,
            href=candidate.href,
            continuation_prompt=candidate.continuation_prompt,
            reason=candidate.reason,
            continuity_score=score,
            project_id=candidate.project_id,
            task_id=candidate.task_id,
            conversation_id=candidate.conversation_id,
            priority=candidate.priority,
            updated_at=candidate.updated_at,
        )

    @staticmethod
    def _project_activity(
        projects: list[Project],
        conversations: list[Conversation],
        tasks: list[Task],
        notes: list[Note],
    ) -> dict[UUID, float]:
        scores: dict[UUID, float] = {project.id: 0.12 for project in projects if project.status == "active"}
        for task in tasks:
            if task.project_id and task.status in OPEN_STATUSES:
                scores[task.project_id] = scores.get(task.project_id, 0.0) + 0.18
        for conversation in conversations:
            if conversation.project_id and conversation.archived_at is None:
                scores[conversation.project_id] = scores.get(conversation.project_id, 0.0) + 0.12
        for note in notes:
            if note.project_id:
                scores[note.project_id] = scores.get(note.project_id, 0.0) + 0.06
        return {project_id: min(score, 1.0) for project_id, score in scores.items()}

    @staticmethod
    def _memory_topics(memories: list[Memory]) -> set[str]:
        text = " ".join(
            f"{memory.memory_type} {memory.category or ''} {memory.summary or ''} {memory.content}"
            for memory in memories[:12]
            if (memory.memory_type or memory.category or "").lower() in MEMORY_TYPES_WITH_CONTINUITY_VALUE or memory.importance_score >= 0.55
        )
        return {token for token in tokenize(text) if len(token) > 4}

    @staticmethod
    def _topic_overlap(title: str, detail: str, memory_topics: set[str]) -> float:
        if not memory_topics:
            return 0.0
        tokens = {token for token in tokenize(f"{title} {detail}") if len(token) > 4}
        if not tokens:
            return 0.0
        return min(len(tokens & memory_topics) / max(len(tokens), 1) * 2.5, 1.0)

    @staticmethod
    def _recency_score(value: datetime | None) -> float:
        if not value:
            return 0.0
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        age_days = max((datetime.now(timezone.utc) - value).days, 0)
        return 1.0 / (1.0 + age_days * 0.12)

    @staticmethod
    def _count_by_project(items) -> dict[UUID, int]:
        counts: dict[UUID, int] = {}
        for item in items:
            if item.project_id:
                counts[item.project_id] = counts.get(item.project_id, 0) + 1
        return counts

    @staticmethod
    def _task_status_summary(task: Task) -> str:
        if task.status == "in_progress":
            return "In progress and ready to continue."
        if task.due_at:
            return "Open task with a due date."
        return "Unfinished work to carry forward."

    @staticmethod
    def _task_reason(task: Task) -> str:
        if task.status == "in_progress":
            return "Already in progress."
        if task.due_at:
            return "Timed unfinished work."
        if task.priority == "high":
            return "High-priority unfinished work."
        return "Unfinished task."

    @staticmethod
    def _due_pressure(value: datetime | None) -> float:
        if not value:
            return 0.0
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        days_until_due = (value - datetime.now(timezone.utc)).days
        if days_until_due < 0:
            return 1.0
        if days_until_due == 0:
            return 0.85
        return max(0.0, 0.7 - days_until_due * 0.12)

    @staticmethod
    def _project_reason(open_count: int, thread_count: int) -> str:
        parts: list[str] = []
        if open_count:
            parts.append(f"{open_count} open task{'s' if open_count != 1 else ''}")
        if thread_count:
            parts.append(f"{thread_count} recent thread{'s' if thread_count != 1 else ''}")
        return "; ".join(parts) or "Active project context."
