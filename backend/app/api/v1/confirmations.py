from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.confirmation import ConfirmationDecisionResponse, ConfirmationOut
from app.services.confirmation_service import ConfirmationService
from app.services.tool_system_service import ToolSystemService

router = APIRouter(prefix="/confirmations")


@router.get("/pending", response_model=list[ConfirmationOut])
async def list_pending_confirmations(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    rows = await ConfirmationService.pending_for_user(session, user.id)
    return [
        ConfirmationOut(
            id=row.id,
            user_id=row.user_id,
            requested_action=row.requested_action,
            tool_name=row.tool_name,
            tool_arguments=row.tool_arguments,
            human_readable_summary=row.human_readable_summary,
            risk_level=row.risk_level,
            status=row.status,
            created_at=row.created_at,
            expires_at=row.expires_at,
        )
        for row in rows
    ]


@router.post("/{confirmation_id}/confirm", response_model=ConfirmationDecisionResponse)
async def confirm_action(
    confirmation_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        confirmation = await ConfirmationService.confirm(session, confirmation_id=confirmation_id, user_id=user.id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="This confirmation does not belong to you") from None
    except TimeoutError:
        raise HTTPException(status_code=410, detail="This confirmation has expired") from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None

    tool_result = await ToolSystemService().execute_tool_request(
        confirmation.tool_name,
        confirmation.tool_arguments,
        user_id=user.id,
        conversation_context={"confirmation_id": str(confirmation.id)},
    )
    if tool_result.get("success"):
        confirmation.status = "executed"
        await ConfirmationService.record_activity(session, confirmation, "confirmation_executed")
        await session.commit()
        return ConfirmationDecisionResponse(ok=True, confirmation_id=confirmation.id, status="executed", message="Confirmation accepted and the action completed successfully.")

    confirmation.status = "failed"
    await ConfirmationService.record_activity(session, confirmation, "confirmation_failed")
    await session.commit()
    return ConfirmationDecisionResponse(ok=False, confirmation_id=confirmation.id, status="failed", message=tool_result.get("error") or "The action could not be executed after confirmation.")


@router.post("/{confirmation_id}/reject", response_model=ConfirmationDecisionResponse)
async def reject_action(
    confirmation_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        confirmation = await ConfirmationService.reject(session, confirmation_id=confirmation_id, user_id=user.id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="This confirmation does not belong to you") from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    await session.commit()
    return ConfirmationDecisionResponse(ok=True, confirmation_id=confirmation.id, status=confirmation.status, message="The action was rejected and will not execute.")
