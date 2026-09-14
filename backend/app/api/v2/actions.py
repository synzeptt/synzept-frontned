from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.infrastructure.jobs import JobType, enqueue
from app.models.user import User
from app.services.chat_service import ChatService
from app.schemas.actions import ActionExecutionOut
from app.services.action_execution_service import ActionExecutionService

router = APIRouter(prefix="/actions")


class ActionExecutionCreateRequest(BaseModel):
    request: str
    action_type: str | None = None
    project_id: UUID | None = None
    conversation_id: UUID | None = None
    metadata: dict = Field(default_factory=dict)


class EmailDraftUpdateRequest(BaseModel):
    draft_index: int = Field(ge=0)
    to: str | None = None
    subject: str | None = None
    suggested_reply: str | None = None


class ActionApprovalRequest(BaseModel):
    draft_indices: list[int] | None = Field(default=None, min_length=1)


@router.get("", response_model=list[ActionExecutionOut])
async def list_actions(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ActionExecutionService(session).list(user.id)


@router.get("/{action_id}", response_model=ActionExecutionOut)
async def get_action(action_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    action = await ActionExecutionService(session)._owned(user.id, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.post("", response_model=ActionExecutionOut)
async def create_action(body: ActionExecutionCreateRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    chat = ChatService(session)
    conversation = await chat.get_or_create(user.id, body.conversation_id, body.project_id)
    existing_messages = await chat.get_messages(conversation.id)
    proposal_already_saved = any(
        message.role == "user"
        and message.content == body.request
        and ((message.metadata_ or {}).get("kind") == "proposal" or (message.metadata_ or {}).get("execution_request") is True)
        for message in existing_messages
    )
    if not proposal_already_saved:
        await chat.add_message(conversation.id, "user", body.request, metadata={"execution_request": True})
    action = await ActionExecutionService(session).create_for_request(
        user_id=user.id,
        conversation_id=conversation.id,
        project_id=body.project_id,
        message=body.request,
        action_type=body.action_type,
        metadata=body.metadata,
    )
    if not action:
        raise HTTPException(status_code=400, detail="Could not classify this request as an AI action.")
    acknowledgement = "I'm getting that ready. I'll keep you updated as the result is produced."
    if action.action_type == "meeting_preparation":
        acknowledgement = "I'm preparing your briefing and checking the relevant context."
    elif action.status in {"awaiting_confirmation", "waiting_approval"}:
        acknowledgement = "The action is ready and needs your approval before I continue."
    await chat.add_message(
        conversation.id,
        "assistant",
        acknowledgement,
        metadata={"execution_acknowledgement": True, "action_id": str(action.id)},
    )
    await session.commit()

    # If a deduped action got stuck in an intermediate stage from an earlier failed run,
    # reset it so the worker can retry it cleanly.
    if action.status == "planning":
        action.status = "queued"
        action.progress = 0
        action.output = None
        action.error = None
        action.started_at = None
        action.completed_at = None
        action.failed_at = None
        action.cancelled_at = None
        await session.flush()
        await session.commit()

    if action.status == "queued":
        enqueue(JobType.ACTION_EXECUTE, action_id=action.id)
    return action


@router.post("/{action_id}/retry", response_model=ActionExecutionOut)
async def retry_action(action_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    action = await ActionExecutionService(session).retry(user.id, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    await session.commit()
    enqueue(JobType.ACTION_EXECUTE, action_id=action.id)
    return action


@router.post("/{action_id}/approve", response_model=ActionExecutionOut)
async def approve_action(action_id: UUID, body: ActionApprovalRequest | None = None, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    action = await ActionExecutionService(session).approve(user.id, action_id, body.draft_indices if body else None)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    enqueue(JobType.ACTION_EXECUTE, action_id=action.id)
    await session.commit()
    await session.refresh(action)
    return action


@router.patch("/{action_id}/email-draft", response_model=ActionExecutionOut)
async def update_email_draft(action_id: UUID, body: EmailDraftUpdateRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    try:
        action = await ActionExecutionService(session).update_email_draft(user.id, action_id, body.draft_index, body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not action:
        raise HTTPException(status_code=404, detail="Email draft not found")
    await session.commit()
    await session.refresh(action)
    return action


@router.post("/{action_id}/reject", response_model=ActionExecutionOut)
async def reject_action(action_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    action = await ActionExecutionService(session).reject(user.id, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    await session.commit()
    await session.refresh(action)
    return action


@router.post("/{action_id}/cancel", response_model=ActionExecutionOut)
async def cancel_action(action_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    action = await ActionExecutionService(session).cancel(user.id, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.get("/{action_id}/artifacts")
async def get_action_artifacts(action_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Get artifacts associated with an action."""
    action = await ActionExecutionService(session)._owned(user.id, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    metadata = action.metadata_ or {}
    artifacts = metadata.get("artifacts", [])
    
    return {
        "action_id": str(action.id),
        "artifacts": artifacts,
        "total_artifacts": len(artifacts),
    }


@router.get("/{action_id}/download/{artifact_id}")
async def download_action_artifact(
    action_id: UUID,
    artifact_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Download an artifact file from a completed action."""
    import os
    from fastapi.responses import FileResponse
    
    action = await ActionExecutionService(session)._owned(user.id, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    metadata = action.metadata_ or {}
    artifacts = metadata.get("artifacts", [])
    
    # Find the artifact
    artifact = None
    for art in artifacts:
        if art.get("id") == artifact_id or art.get("artifact_id") == artifact_id:
            artifact = art
            break
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    file_path = artifact.get("file_path") or artifact.get("storage_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Verify the file belongs to the user
    if str(user.id) not in os.path.realpath(file_path).split(os.sep):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    filename = os.path.basename(file_path)
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=artifact.get("file_type", "application/octet-stream"),
    )

