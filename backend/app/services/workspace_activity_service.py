from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace_activity import WorkspaceActivity


class WorkspaceActivityService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        *,
        user_id: UUID,
        action: str,
        title: str,
        detail: str = "",
        project_id: UUID | None = None,
        goal_id: UUID | None = None,
        task_id: UUID | None = None,
        note_id: UUID | None = None,
        metadata: dict | None = None,
    ) -> WorkspaceActivity:
        item = WorkspaceActivity(
            user_id=user_id,
            action=action,
            title=title,
            detail=detail,
            project_id=project_id,
            goal_id=goal_id,
            task_id=task_id,
            note_id=note_id,
            metadata_=metadata or {},
        )
        self.session.add(item)
        await self.session.flush()
        return item
