from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.context_engine_phase6 import ContextSnapshot
from app.models.learning import LearningSuggestion
from app.models.project import Project
from app.models.project_intelligence_phase2 import OpenLoop
from app.models.relationship_graph_phase5 import RelationshipEdge, RelationshipNode
from app.models.timeline_event import TimelineEvent
from app.models.user_understanding import UserUnderstanding


class ContextEnginePhase6Service:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def current(self, user_id: UUID) -> dict:
        snapshot = await self._latest_snapshot(user_id)
        if snapshot:
            return self._snapshot_out(snapshot)
        return await self.refresh(user_id)

    async def refresh(self, user_id: UUID) -> dict:
        profile = await self._understanding(user_id)
        projects = await self._projects(user_id)
        open_loops = await self._open_loops(user_id)
        timeline = await self._timeline(user_id)
        suggestions = await self._suggestions(user_id)
        graph = await self._relationship_context(user_id)

        payload = self._build_context(user_id, profile, projects, open_loops, timeline, suggestions, graph)
        snapshot = ContextSnapshot(
            user_id=user_id,
            current_focus=payload["currentFocus"],
            active_themes=payload["activeThemes"],
            open_loops=payload["openLoops"],
            important_context=payload["importantContext"],
            recommended_next_step=payload["recommendedNextStep"],
        )
        self.session.add(snapshot)
        await self.session.flush()
        return self._snapshot_out(snapshot)

    async def _latest_snapshot(self, user_id: UUID) -> ContextSnapshot | None:
        result = await self.session.execute(
            select(ContextSnapshot).where(ContextSnapshot.user_id == user_id).order_by(ContextSnapshot.created_at.desc())
        )
        return result.scalars().first()

    async def _understanding(self, user_id: UUID) -> UserUnderstanding | None:
        result = await self.session.execute(select(UserUnderstanding).where(UserUnderstanding.user_id == user_id))
        return result.scalars().first()

    async def _projects(self, user_id: UUID) -> list[Project]:
        result = await self.session.execute(
            select(Project)
            .where(Project.user_id == user_id, Project.status.in_(["active", "paused"]))
            .order_by(Project.updated_at.desc())
        )
        return list(result.scalars())

    async def _open_loops(self, user_id: UUID) -> list[tuple[OpenLoop, Project]]:
        result = await self.session.execute(
            select(OpenLoop, Project)
            .join(Project, Project.id == OpenLoop.project_id)
            .where(Project.user_id == user_id, OpenLoop.status == "open")
            .order_by(OpenLoop.updated_at.desc())
        )
        return list(result.all())

    async def _timeline(self, user_id: UUID) -> list[TimelineEvent]:
        result = await self.session.execute(
            select(TimelineEvent)
            .where(TimelineEvent.user_id == user_id)
            .order_by(TimelineEvent.event_date.desc(), TimelineEvent.created_at.desc())
            .limit(8)
        )
        return list(result.scalars())

    async def _suggestions(self, user_id: UUID) -> list[LearningSuggestion]:
        result = await self.session.execute(
            select(LearningSuggestion)
            .where(LearningSuggestion.user_id == user_id)
            .order_by(LearningSuggestion.updated_at.desc())
            .limit(8)
        )
        return list(result.scalars())

    async def _relationship_context(self, user_id: UUID) -> list[tuple[RelationshipEdge, RelationshipNode, RelationshipNode]]:
        source_node = aliased(RelationshipNode)
        target_node = aliased(RelationshipNode)
        result = await self.session.execute(
            select(RelationshipEdge, source_node, target_node)
            .join(source_node, source_node.id == RelationshipEdge.source_node_id)
            .join(target_node, target_node.id == RelationshipEdge.target_node_id)
            .where(RelationshipEdge.user_id == user_id)
            .order_by(RelationshipEdge.updated_at.desc())
            .limit(8)
        )
        return list(result.all())

    def _build_context(
        self,
        user_id: UUID,
        profile: UserUnderstanding | None,
        projects: list[Project],
        open_loops: list[tuple[OpenLoop, Project]],
        timeline: list[TimelineEvent],
        suggestions: list[LearningSuggestion],
        graph: list[tuple[RelationshipEdge, RelationshipNode, RelationshipNode]],
    ) -> dict:
        focus_project = next((project for project in projects if project.current_focus.strip()), projects[0] if projects else None)
        profile_focus = (profile.current_focus or {}) if profile else {}
        current_focus = {
            "source": "project" if focus_project else "user_understanding",
            "title": focus_project.name if focus_project else profile_focus.get("mainFocus", "No current focus set."),
            "detail": focus_project.current_focus if focus_project else profile_focus.get("mainFocus", ""),
            "projectId": str(focus_project.id) if focus_project else None,
        }

        active_themes = []
        for project in projects[:4]:
            active_themes.append({"type": "project", "title": project.name, "detail": project.current_focus or project.description or ""})
        for suggestion in suggestions:
            if suggestion.status in {"pending", "accepted"}:
                active_themes.append({"type": f"learning_{suggestion.status}", "title": suggestion.title, "detail": suggestion.description})
        for event in timeline[:3]:
            active_themes.append({"type": f"timeline_{event.event_type}", "title": event.title, "detail": event.description})

        open_loop_items = [
            {
                "id": str(loop.id),
                "projectId": str(project.id),
                "projectName": project.name,
                "title": loop.title,
                "description": loop.description,
            }
            for loop, project in open_loops
        ]

        important_context = []
        if profile:
            for label, value in (
                ("personal", profile.personal),
                ("professional", profile.professional),
                ("goals", profile.goals),
                ("preferences", profile.preferences),
                ("learning", profile.learning),
            ):
                if value:
                    important_context.append({"type": "user_understanding", "title": label, "detail": value})
        for edge, source, target in graph:
            important_context.append(
                {
                    "type": "relationship",
                    "title": f"{source.title} -> {target.title}",
                    "detail": edge.reason or edge.relationship_type,
                    "strength": edge.strength,
                }
            )

        next_project = next((project for project in projects if project.recommended_next_step.strip()), None)
        if next_project:
            recommended_next_step = {
                "source": "project",
                "title": next_project.recommended_next_step,
                "projectId": str(next_project.id),
                "reason": f"Recommended next step for {next_project.name}.",
            }
        elif open_loop_items:
            recommended_next_step = {
                "source": "open_loop",
                "title": open_loop_items[0]["title"],
                "projectId": open_loop_items[0]["projectId"],
                "reason": "Oldest visible unfinished loop keeps continuity moving.",
            }
        else:
            recommended_next_step = {
                "source": "empty_state",
                "title": "Define the next action to keep momentum.",
                "projectId": None,
                "reason": "No project next step or open loop is available.",
            }

        return {
            "userId": user_id,
            "currentFocus": current_focus,
            "activeThemes": active_themes[:10],
            "openLoops": open_loop_items[:10],
            "importantContext": important_context[:12],
            "recommendedNextStep": recommended_next_step,
        }

    @staticmethod
    def _snapshot_out(snapshot: ContextSnapshot) -> dict:
        now = datetime.now(timezone.utc)
        return {
            "id": snapshot.id,
            "userId": snapshot.user_id,
            "currentFocus": snapshot.current_focus or {},
            "activeThemes": snapshot.active_themes or [],
            "openLoops": snapshot.open_loops or [],
            "importantContext": snapshot.important_context or [],
            "recommendedNextStep": snapshot.recommended_next_step or {},
            "createdAt": snapshot.created_at or now,
            "updatedAt": snapshot.updated_at or snapshot.created_at or now,
        }
