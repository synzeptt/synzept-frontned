"""Coordinates recent history, memory, profile, project, and task context."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.project import Project
from app.models.project_intelligence_phase2 import Decision, OpenLoop
from app.models.task import Task
from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.memory.memory_service import MemoryService
from app.services.goal_progress_service import GoalProgressService
from app.orchestrator.conversation_intelligence import ConversationIntelligenceService
from app.orchestrator.intent_service import OrchestrationIntent, OrchestrationIntentCategory
from app.tasks.service import OPEN_STATUSES
from app.orchestrator.project_context_service import ProjectContextBundle, ProjectContextService
from app.retrieval.retrieval_service import RetrievalFilters, SemanticRetrievalService
from app.services.autonomous_workspace_service import AutonomousWorkspaceService
from app.services.relationship_graph_phase5_service import RelationshipGraphPhase5Service
from app.services.proactive_intelligence_service import ProactiveIntelligenceService
from app.utils.text import truncate
from app.infrastructure.monitoring import monitor

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ContextBundle:
    user_profile: str = ""
    conversation_summary: str = ""
    recent_messages: list[dict[str, str]] = field(default_factory=list)
    memories: list[str] = field(default_factory=list)
    continuation_context: list[str] = field(default_factory=list)
    conversation_intelligence: list[str] = field(default_factory=list)
    personalization: list[str] = field(default_factory=list)
    progress_context: list[str] = field(default_factory=list)
    personal_intelligence: list[str] = field(default_factory=list)
    graph_context: list[str] = field(default_factory=list)
    chief_of_staff_context: list[str] = field(default_factory=list)
    autonomous_workspace_context: list[str] = field(default_factory=list)
    trust_context: dict = field(default_factory=dict)
    project: ProjectContextBundle = field(default_factory=ProjectContextBundle)


class ContextBuilder:
    def __init__(
        self,
        session: AsyncSession,
        *,
        retrieval: SemanticRetrievalService | None = None,
        projects: ProjectContextService | None = None,
    ) -> None:
        self.session = session
        self.retrieval = retrieval or SemanticRetrievalService(session)
        self.projects = projects or ProjectContextService(session)
        self.conversation_intel = ConversationIntelligenceService(session)

    async def build(
        self,
        *,
        user_id: UUID,
        message: str,
        conversation: Conversation,
        intent: OrchestrationIntent,
        project_id: UUID | None,
    ) -> ContextBundle:
        user = await self.session.get(User, user_id)
        preferences = user.preferences or {} if user else {}
        memory_enabled = preferences.get("memory_enabled", True) and preferences.get("personalization_enabled", True)
        project_context = await self.projects.get_context(
            user_id=user_id,
            project_id=project_id,
            include_tasks=intent.strategy.include_tasks,
        )
        filters = RetrievalFilters(
            project_id=project_id,
            limit=intent.strategy.memory_limit,
            min_score=0.32,
        )
        ranked = []
        if memory_enabled:
            try:
                with monitor.timed("retrieval.context", project_id=str(project_id) if project_id else None):
                    ranked = await self.retrieval.retrieve(user_id=user_id, query=message, filters=filters)
            except Exception as exc:
                logger.warning(
                    "semantic retrieval failed; using lexical fallback",
                    extra={"operation": "retrieval", "error_code": exc.__class__.__name__},
                )
                with monitor.timed("retrieval.lexical_fallback", project_id=str(project_id) if project_id else None):
                    ranked = await self.retrieval.lexical_fallback(user_id=user_id, query=message, filters=filters)
        return ContextBundle(
            user_profile=await self._user_profile(user_id),
            conversation_summary=conversation.summary or "",
            recent_messages=await self._recent_messages(conversation.id, limit=intent.strategy.recent_message_limit),
            memories=[
                truncate(f"[{item.memory.memory_type}] {item.memory.summary or item.memory.content}", 320)
                for item in ranked
            ],
            continuation_context=await self._continuation_context(
                user_id=user_id,
                intent=intent,
                project_id=active_project_id(project_id, conversation.project_id),
            ),
            conversation_intelligence=await self.conversation_intel.related_context(
                user_id=user_id,
                query=message,
                current_conversation_id=conversation.id,
                project_id=active_project_id(project_id, conversation.project_id),
                limit=6,
            ),
            personalization=self._personalization_cues(user, ranked),
            progress_context=await self._progress_context(user_id),
            personal_intelligence=await self._personal_intelligence_context(user_id),
            graph_context=await self._graph_context(user_id, clean_query(message)),
            chief_of_staff_context=await self._chief_of_staff_context(user_id),
            autonomous_workspace_context=await self._autonomous_workspace_context(user_id),
            trust_context=await self._trust_context(
                user_id=user_id,
                ranked=ranked,
                project_id=active_project_id(project_id, conversation.project_id),
            ),
            project=project_context,
        )

    async def _user_profile(self, user_id: UUID) -> str:
        user = await self.session.get(User, user_id)
        if not user:
            return ""
        preferences = user.preferences or {}
        if preferences.get("personalization_enabled", True) is False:
            return ""
        profile_lines = [user.profile_summary] if user.profile_summary else []
        memories = await MemoryService(self.session).search_memory(user_id=user_id, limit=30)
        grouped: dict[str, list[str]] = {}
        for memory in memories:
            if memory.category not in {"goals", "projects", "interests", "skills", "long_term_plans"}:
                continue
            grouped.setdefault(memory.category, []).append(memory.summary or memory.content)
        for category, values in grouped.items():
            profile_lines.append(f"{category.replace('_', ' ').title()}: " + "; ".join(values[:4]))
        return truncate("\n".join(profile_lines), 700)

    async def _recent_messages(self, conversation_id: UUID, *, limit: int) -> list[dict[str, str]]:
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = list(result.scalars().all())
        messages.reverse()
        return [{"role": message.role, "content": truncate(message.content, 1200)} for message in messages]

    @staticmethod
    def _personalization_cues(user: User | None, ranked) -> list[str]:
        cues: list[str] = []
        preferences = user.preferences or {} if user else {}
        style = preferences.get("communication_style") or preferences.get("response_depth")
        if style:
            cues.append(f"Communication preference: {style}.")
        for item in ranked:
            memory = item.memory
            if memory.memory_type in {"preferences", "routines"}:
                cues.append(truncate(memory.summary or memory.content, 180))
            if len(cues) >= 4:
                break
        return cues

    async def _continuation_context(
        self,
        *,
        user_id: UUID,
        intent: OrchestrationIntent,
        project_id: UUID | None,
    ) -> list[str]:
        if intent.category not in {
            OrchestrationIntentCategory.PROJECT_CONTINUATION,
            OrchestrationIntentCategory.PLANNING,
            OrchestrationIntentCategory.ORGANIZATION,
            OrchestrationIntentCategory.TASK_ASSISTANCE,
        }:
            return []

        clauses = [Conversation.user_id == user_id, Conversation.deleted_at.is_(None), Conversation.archived_at.is_(None)]
        if project_id:
            clauses.append(Conversation.project_id == project_id)
        conversation_result = await self.session.execute(
            select(Conversation).where(*clauses).order_by(Conversation.updated_at.desc()).limit(3)
        )

        task_clauses = [Task.user_id == user_id, Task.deleted_at.is_(None), Task.status.in_(OPEN_STATUSES)]
        if project_id:
            task_clauses.append(Task.project_id == project_id)
        task_result = await self.session.execute(
            select(Task).where(*task_clauses).order_by(Task.updated_at.desc()).limit(5)
        )

        project_result = None
        if project_id:
            project_result = await self.session.execute(
                select(Project).where(Project.id == project_id, Project.user_id == user_id, Project.deleted_at.is_(None)).limit(1)
            )

        lines: list[str] = []
        if project_result:
            project = project_result.scalar_one_or_none()
            if project:
                detail = truncate(project.context_summary or project.description or "", 260)
                lines.append(f"Active project to restore: {project.name}. {detail}".strip())

        for conversation in conversation_result.scalars().all():
            detail = truncate(conversation.summary or conversation.active_intent or "", 260)
            if detail:
                lines.append(f"Recent discussion: {conversation.title or 'Untitled conversation'} - {detail}")

        for task in task_result.scalars().all():
            descriptor = f"{task.status.replace('_', ' ')}, {task.priority} priority"
            if task.description:
                descriptor += f": {truncate(task.description, 160)}"
            lines.append(f"Unfinished task: {task.title} ({descriptor})")

        return lines[:8]

    async def _progress_context(self, user_id: UUID) -> list[str]:
        service = GoalProgressService(self.session)
        goals = await service.list_goals(user_id, status="active")
        actions = await service.next_actions(user_id, limit=4)
        lines = [f"Active goal: {goal.title} ({goal.progress:.0f}% complete)" for goal in goals[:4]]
        lines.extend(f"Recommended next action: {action.title} - {action.reason}" for action in actions)
        return lines[:8]

    async def _personal_intelligence_context(self, user_id: UUID) -> list[str]:
        understanding_result = await self.session.execute(
            select(UserUnderstanding)
            .where(UserUnderstanding.user_id == user_id)
            .order_by(UserUnderstanding.updated_at.desc())
            .limit(40)
        )
        tasks_result = await self.session.execute(
            select(Task)
            .where(Task.user_id == user_id, Task.deleted_at.is_(None), Task.status.in_(OPEN_STATUSES))
            .order_by(Task.updated_at.desc())
            .limit(6)
        )
        projects = await self.session.execute(
            select(Project)
            .where(Project.user_id == user_id, Project.deleted_at.is_(None), Project.status == "active")
            .order_by(Project.updated_at.desc())
            .limit(6)
        )
        active_projects = list(projects.scalars().all())
        project_ids = [project.id for project in active_projects]
        decisions: list[Decision] = []
        loops: list[OpenLoop] = []
        if project_ids:
            decision_result = await self.session.execute(
                select(Decision)
                .where(Decision.project_id.in_(project_ids))
                .order_by(Decision.updated_at.desc())
                .limit(8)
            )
            loop_result = await self.session.execute(
                select(OpenLoop)
                .where(OpenLoop.project_id.in_(project_ids), OpenLoop.status == "open")
                .order_by(OpenLoop.updated_at.desc())
                .limit(8)
            )
            decisions = list(decision_result.scalars().all())
            loops = list(loop_result.scalars().all())
        understanding = list(understanding_result.scalars().all())
        tasks = list(tasks_result.scalars().all())
        lines: list[str] = []
        mission = self._first_understanding(
            understanding,
            titles=("Current Mission", "Mission", "North Star", "Long-Term Goals", "Short-Term Goals"),
            categories=("current_mission", "goals"),
        )
        focus = self._first_understanding(
            understanding,
            titles=("Current Focus", "Current Priorities", "Active Projects"),
            categories=("current_focus", "recent_priorities"),
        )
        if mission:
            lines.append(f"Current mission: {mission}")
        if focus:
            lines.append(f"Current focus: {focus}")
        if active_projects:
            lines.append("Active projects: " + "; ".join(project.name for project in active_projects[:4]))
        if tasks:
            lines.append("Top unfinished work: " + "; ".join(task.title for task in tasks[:4]))
        pending_decisions = [decision for decision in decisions if decision.status == "pending"]
        decided = [decision for decision in decisions if decision.status == "decided"]
        if loops:
            lines.append("Open loops: " + "; ".join(loop.title for loop in loops[:4]))
        if pending_decisions:
            lines.append("Pending decisions: " + "; ".join(decision.title for decision in pending_decisions[:3]))
        if decided:
            lines.append(
                "Recent decisions: "
                + "; ".join(
                    f"{decision.title}"
                    + (f" because {decision.reason}" if decision.reason else "")
                    + (f" outcome: {decision.outcome}" if decision.outcome else "")
                    for decision in decided[:3]
                )
            )
        return [truncate(line, 380) for line in lines[:8]]

    async def _graph_context(self, user_id: UUID, query: str) -> list[str]:
        try:
            context = await RelationshipGraphPhase5Service(self.session).context_for_query(user_id, query, limit=10)
        except Exception as exc:
            logger.warning("relationship graph context failed", extra={"operation": "graph_context", "error_code": exc.__class__.__name__})
            return []
        items = [
            *context.blockers[:4],
            *context.decisions[:4],
            *context.supportingContext[:4],
            *context.nextActions[:4],
        ]
        seen: set[str] = set()
        lines: list[str] = []
        for item in items:
            key = f"{item.nodeType}:{item.title}:{item.relationshipType}"
            if key in seen:
                continue
            seen.add(key)
            lines.append(
                truncate(
                    f"{item.nodeType.replace('_', ' ').title()}: {item.title} "
                    f"({item.relationshipType.replace('_', ' ')}; {item.reason or item.description})",
                    360,
                )
            )
            if len(lines) >= 8:
                break
        return lines

    async def _chief_of_staff_context(self, user_id: UUID) -> list[str]:
        try:
            chief = await ProactiveIntelligenceService(self.session).chief_of_staff(user_id, persist=False)
        except Exception as exc:
            logger.warning("chief of staff context failed", extra={"operation": "chief_of_staff_context", "error_code": exc.__class__.__name__})
            return []
        lines: list[str] = []
        if chief.executive_brief.recommended_next_action:
            action = chief.executive_brief.recommended_next_action
            lines.append(f"Recommended next action: {action.title} - {action.detail}")
        lines.extend(f"Risk: {item.title} - {item.detail}" for item in chief.risks[:3])
        lines.extend(f"Opportunity: {item.title} - {item.detail}" for item in chief.opportunities[:3])
        lines.extend(f"Commitment: {item.title} ({item.status})" for item in chief.commitments[:3])
        lines.append(f"Momentum: {chief.momentum.score}/100, trend {chief.momentum.trend}. {chief.momentum.explanation}")
        return [truncate(line, 360) for line in lines[:9]]

    async def _autonomous_workspace_context(self, user_id: UUID) -> list[str]:
        try:
            service = AutonomousWorkspaceService(self.session)
            execution = await service.execution_state(user_id)
            weekly = await service.weekly_plan(user_id)
            suggestions = await service.generate_suggestions(user_id)
        except Exception as exc:
            logger.warning("autonomous workspace context failed", extra={"operation": "autonomous_workspace_context", "error_code": exc.__class__.__name__})
            return []

        lines = [f"Execution state: {len(execution.planned)} planned, {len(execution.completed)} completed, {len(execution.blocked)} blocked."]
        if weekly.priority_focus:
            lines.append(f"Weekly priority focus: {weekly.priority_focus}")
        lines.extend(f"This week: {item.title} - {item.detail}" for item in weekly.this_week[:3])
        lines.extend(f"Next week: {item.title} - {item.detail}" for item in weekly.next_week[:2])
        lines.extend(f"Autonomous suggestion: {item.title} - {item.detail}" for item in suggestions[:3])
        return [truncate(line, 360) for line in lines[:9]]

    async def _trust_context(self, *, user_id: UUID, ranked, project_id: UUID | None) -> dict:
        memories = [
            {
                "id": str(item.memory.id),
                "content": truncate(item.memory.summary or item.memory.content, 180),
                "confidence": item.memory.confidence,
                "source": item.memory.source,
            }
            for item in ranked[:8]
        ]
        projects: list[str] = []
        open_loops: list[str] = []
        decisions: list[str] = []
        if project_id:
            projects.append(str(project_id))
            loops = await self.session.execute(select(OpenLoop.id).where(OpenLoop.project_id == project_id, OpenLoop.status == "open").limit(8))
            decision_rows = await self.session.execute(select(Decision.id).where(Decision.project_id == project_id).order_by(Decision.updated_at.desc()).limit(8))
            open_loops = [str(item) for item in loops.scalars()]
            decisions = [str(item) for item in decision_rows.scalars()]
        return {"memories": memories, "projects": projects, "open_loops": open_loops, "decisions": decisions}

    @staticmethod
    def _first_understanding(
        items: list[UserUnderstanding],
        *,
        titles: tuple[str, ...],
        categories: tuple[str, ...],
    ) -> str:
        title_keys = {title.casefold() for title in titles}
        category_keys = {category.casefold() for category in categories}
        for item in items:
            if item.title.casefold() in title_keys or item.category.casefold() in category_keys:
                lines = [line.strip(" -*\t") for line in item.value.replace(";", "\n").splitlines() if line.strip(" -*\t")]
                if lines:
                    return lines[0]
        return ""


def active_project_id(explicit_project_id: UUID | None, conversation_project_id: UUID | None) -> UUID | None:
    return explicit_project_id or conversation_project_id


def clean_query(value: str) -> str:
    return truncate(value, 400)
