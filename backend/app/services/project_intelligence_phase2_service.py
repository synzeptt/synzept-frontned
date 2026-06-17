from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.project import Project
from app.models.project_intelligence_phase2 import Decision, OpenLoop
from app.schemas.project_intelligence_phase2 import (
    DecisionCreate,
    DecisionUpdate,
    OpenLoopCreate,
    OpenLoopUpdate,
    ProjectCreatePhase2,
    ProjectUpdatePhase2,
)
from app.services.workspace_activity_service import WorkspaceActivityService


class ProjectIntelligencePhase2Service:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.activity = WorkspaceActivityService(session)

    async def list_projects(self, user_id: UUID) -> list[dict]:
        result = await self.session.execute(
            select(Project)
            .where(Project.user_id == user_id, Project.deleted_at.is_(None))
            .order_by(Project.updated_at.desc())
        )
        return [self._project_out(project) for project in result.scalars()]

    async def create_project(self, user_id: UUID, data: ProjectCreatePhase2) -> dict:
        project = Project(
            user_id=user_id,
            name=data.name.strip(),
            description=data.description.strip(),
            current_focus=data.currentFocus.strip(),
            recommended_next_step=data.recommendedNextStep.strip(),
            status=data.status,
        )
        self.session.add(project)
        await self.session.flush()
        await self.activity.record(user_id=user_id, action="project_created", title=project.name, detail=project.current_focus or project.description or "", project_id=project.id)
        return self._project_out(project)

    async def get_project(self, user_id: UUID, project_id: UUID) -> dict:
        return self._project_out(await self._owned_project(user_id, project_id))

    async def update_project(self, user_id: UUID, project_id: UUID, data: ProjectUpdatePhase2) -> dict:
        project = await self._owned_project(user_id, project_id)
        updates = data.model_dump(exclude_unset=True)
        if "name" in updates and updates["name"] is not None:
            project.name = updates["name"].strip()
        if "description" in updates and updates["description"] is not None:
            project.description = updates["description"].strip()
        if "currentFocus" in updates and updates["currentFocus"] is not None:
            project.current_focus = updates["currentFocus"].strip()
        if "recommendedNextStep" in updates and updates["recommendedNextStep"] is not None:
            project.recommended_next_step = updates["recommendedNextStep"].strip()
        if "status" in updates and updates["status"] is not None:
            project.status = updates["status"]
        project.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.activity.record(user_id=user_id, action="project_updated", title=project.name, detail=project.recommended_next_step or project.current_focus or "", project_id=project.id)
        return self._project_out(project)

    async def delete_project(self, user_id: UUID, project_id: UUID) -> None:
        project = await self._owned_project(user_id, project_id)
        project.status = "archived"
        project.deleted_at = datetime.now(timezone.utc)
        project.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.activity.record(user_id=user_id, action="project_archived", title=project.name, project_id=project.id)

    async def list_open_loops(self, user_id: UUID, project_id: UUID) -> list[dict]:
        await self._owned_project(user_id, project_id)
        result = await self.session.execute(
            select(OpenLoop)
            .where(OpenLoop.project_id == project_id, OpenLoop.status != "archived")
            .order_by(OpenLoop.updated_at.desc(), OpenLoop.created_at.desc())
        )
        return [self._open_loop_out(item) for item in result.scalars()]

    async def create_open_loop(self, user_id: UUID, project_id: UUID, data: OpenLoopCreate) -> dict:
        await self._owned_project(user_id, project_id)
        item = OpenLoop(
            project_id=project_id,
            title=data.title.strip(),
            description=data.description.strip(),
            status=data.status,
        )
        self.session.add(item)
        await self.session.flush()
        await self.activity.record(user_id=user_id, action="open_loop_created", title=item.title, detail=item.description or "", project_id=project_id)
        return self._open_loop_out(item)

    async def update_open_loop(self, user_id: UUID, item_id: UUID, data: OpenLoopUpdate) -> dict:
        item = await self._owned_open_loop(user_id, item_id)
        updates = data.model_dump(exclude_unset=True)
        if "title" in updates and updates["title"] is not None:
            item.title = updates["title"].strip()
        if "description" in updates and updates["description"] is not None:
            item.description = updates["description"].strip()
        if "status" in updates and updates["status"] is not None:
            item.status = updates["status"]
        item.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.activity.record(user_id=user_id, action="open_loop_updated", title=item.title, detail=item.description or "", project_id=item.project_id)
        return self._open_loop_out(item)

    async def delete_open_loop(self, user_id: UUID, item_id: UUID) -> None:
        item = await self._owned_open_loop(user_id, item_id)
        item.status = "archived"
        item.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.activity.record(user_id=user_id, action="open_loop_archived", title=item.title, project_id=item.project_id)

    async def list_decisions(self, user_id: UUID, project_id: UUID) -> list[dict]:
        await self._owned_project(user_id, project_id)
        result = await self.session.execute(
            select(Decision).where(Decision.project_id == project_id).order_by(Decision.updated_at.desc(), Decision.created_at.desc())
        )
        return [self._decision_out(item) for item in result.scalars()]

    async def create_decision(self, user_id: UUID, project_id: UUID, data: DecisionCreate) -> dict:
        await self._owned_project(user_id, project_id)
        item = Decision(
            project_id=project_id,
            title=data.title.strip(),
            description=data.description.strip(),
            reason=data.reason.strip(),
            outcome=data.outcome.strip(),
            status=data.status,
            decided_at=datetime.now(timezone.utc) if data.status == "decided" else None,
        )
        self.session.add(item)
        await self.session.flush()
        await self.activity.record(user_id=user_id, action="decision_created", title=item.title, detail=item.description or "", project_id=project_id)
        return self._decision_out(item)

    async def update_decision(self, user_id: UUID, item_id: UUID, data: DecisionUpdate) -> dict:
        item = await self._owned_decision(user_id, item_id)
        updates = data.model_dump(exclude_unset=True)
        if "title" in updates and updates["title"] is not None:
            item.title = updates["title"].strip()
        if "description" in updates and updates["description"] is not None:
            item.description = updates["description"].strip()
        if "reason" in updates and updates["reason"] is not None:
            item.reason = updates["reason"].strip()
        if "outcome" in updates and updates["outcome"] is not None:
            item.outcome = updates["outcome"].strip()
        if "status" in updates and updates["status"] is not None:
            item.status = updates["status"]
            if item.status == "decided" and not item.decided_at:
                item.decided_at = datetime.now(timezone.utc)
            elif item.status == "pending":
                item.decided_at = None
        item.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.activity.record(user_id=user_id, action="decision_updated", title=item.title, detail=item.description or "", project_id=item.project_id)
        return self._decision_out(item)

    async def delete_decision(self, user_id: UUID, item_id: UUID) -> None:
        item = await self._owned_decision(user_id, item_id)
        await self.session.delete(item)
        await self.session.flush()
        await self.activity.record(user_id=user_id, action="decision_deleted", title=item.title, project_id=item.project_id)

    async def _owned_project(self, user_id: UUID, project_id: UUID) -> Project:
        result = await self.session.execute(
            select(Project).where(Project.id == project_id, Project.user_id == user_id, Project.deleted_at.is_(None))
        )
        project = result.scalar_one_or_none()
        if not project:
            raise NotFoundError("Project not found")
        return project

    async def _owned_open_loop(self, user_id: UUID, item_id: UUID) -> OpenLoop:
        result = await self.session.execute(
            select(OpenLoop).join(Project, Project.id == OpenLoop.project_id).where(
                OpenLoop.id == item_id,
                Project.user_id == user_id,
                Project.deleted_at.is_(None),
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("Open loop not found")
        return item

    async def _owned_decision(self, user_id: UUID, item_id: UUID) -> Decision:
        result = await self.session.execute(
            select(Decision).join(Project, Project.id == Decision.project_id).where(
                Decision.id == item_id,
                Project.user_id == user_id,
                Project.deleted_at.is_(None),
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("Decision not found")
        return item

    @staticmethod
    def _project_out(project: Project) -> dict:
        return {
            "id": project.id,
            "userId": project.user_id,
            "name": project.name,
            "description": project.description or "",
            "currentFocus": project.current_focus or "",
            "recommendedNextStep": project.recommended_next_step or "",
            "status": project.status,
            "createdAt": project.created_at,
            "updatedAt": project.updated_at,
        }

    @staticmethod
    def _open_loop_out(item: OpenLoop) -> dict:
        return {
            "id": item.id,
            "projectId": item.project_id,
            "title": item.title,
            "description": item.description or "",
            "status": item.status,
            "createdAt": item.created_at,
            "updatedAt": item.updated_at,
        }

    @staticmethod
    def _decision_out(item: Decision) -> dict:
        return {
            "id": item.id,
            "projectId": item.project_id,
            "title": item.title,
            "description": item.description or "",
            "reason": item.reason or "",
            "outcome": item.outcome or "",
            "status": item.status,
            "decidedAt": item.decided_at,
            "createdAt": item.created_at,
            "updatedAt": item.updated_at,
        }
