from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note
from app.models.workspace_activity import WorkspaceActivity


@dataclass(slots=True)
class Artifact:
    artifact_type: str
    title: str
    content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ArtifactService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, *, user_id: UUID, action_id: UUID | None, task_id: UUID | None, artifacts: list[Artifact]) -> list[Note]:
        saved: list[Note] = []
        for artifact in artifacts:
            note = Note(
                user_id=user_id,
                title=artifact.title,
                content=artifact.content or "",
                summary=(artifact.content or "")[:220].replace("\n", " "),
                tags=["execution", artifact.artifact_type],
            )
            self.session.add(note)
            await self.session.flush()
            if action_id is not None:
                self.session.add(
                    WorkspaceActivity(
                        user_id=user_id,
                        action="artifact_created",
                        title=artifact.title,
                        detail=f"Saved {artifact.artifact_type} artifact",
                        task_id=task_id,
                        note_id=note.id,
                        metadata_={"artifact_type": artifact.artifact_type, "action_id": str(action_id)},
                    )
                )
            saved.append(note)
        return saved
