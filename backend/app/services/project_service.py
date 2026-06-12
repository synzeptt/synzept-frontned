from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.project import Project
from app.schemas.core import CoreProjectCreate, CoreProjectUpdate


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, user_id: UUID) -> list[Project]:
        result = await self.session.execute(select(Project).where(Project.user_id == user_id, Project.deleted_at.is_(None)).order_by(Project.updated_at.desc()))
        return [self._normalize(item) for item in result.scalars()]

    async def get(self, user_id: UUID, item_id: UUID) -> Project:
        result = await self.session.execute(select(Project).where(Project.id == item_id, Project.user_id == user_id, Project.deleted_at.is_(None)))
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("Project not found")
        return self._normalize(item)

    async def create(self, user_id: UUID, data: CoreProjectCreate) -> Project:
        item = Project(user_id=user_id, name=data.title, title=data.title, description=data.description, status=data.status)
        self.session.add(item)
        await self.session.flush()
        return item

    async def update(self, user_id: UUID, item_id: UUID, data: CoreProjectUpdate) -> Project:
        item = await self.get(user_id, item_id)
        values = data.model_dump(exclude_unset=True)
        if "title" in values:
            item.name = values["title"]
        for field, value in values.items():
            setattr(item, field, value)
        await self.session.flush()
        return item

    async def delete(self, user_id: UUID, item_id: UUID) -> None:
        item = await self.get(user_id, item_id)
        item.status = "archived"
        item.deleted_at = datetime.now(timezone.utc)

    @staticmethod
    def _normalize(item: Project) -> Project:
        if not item.title:
            item.title = item.name
        return item
