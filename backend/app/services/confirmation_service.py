from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.confirmation import Confirmation
from app.models.workspace_activity import WorkspaceActivity


class RiskLevel:
    SAFE = "safe"
    CONFIRMATION_REQUIRED = "confirmation_required"


class ConfirmationService:
    """Centralized risk evaluation and approval gating for sensitive actions."""

    _SENSITIVE_KEYWORDS = {
        "purchase",
        "payment",
        "book",
        "booking",
        "reserve",
        "reservation",
        "ticket",
        "email",
        "send message",
        "submit",
        "delete",
        "remove",
        "cancel",
        "publish",
        "post",
        "purchase",
        "checkout",
        "purchase order",
        "pay",
        "transfer",
        "withdraw",
        "refund",
    }
    _SECRET_KEY_FIELDS = {
        "token",
        "tokens",
        "secret",
        "secrets",
        "password",
        "passwd",
        "pwd",
        "api_key",
        "api_key_id",
        "apikey",
        "authorization",
        "auth",
        "cookie",
        "cookies",
        "session_id",
        "session",
        "refresh_token",
        "access_token",
        "id_token",
        "client_secret",
        "jwt",
        "bearer",
    }

    @classmethod
    def evaluate_risk(cls, tool_name: str, parameters: dict[str, Any] | None = None, requested_action: str | None = None) -> str:
        text = " ".join(
            [
                tool_name or "",
                json.dumps(parameters or {}, sort_keys=True),
                requested_action or "",
            ]
        ).lower()

        if any(keyword in text for keyword in cls._SENSITIVE_KEYWORDS):
            return RiskLevel.CONFIRMATION_REQUIRED
        return RiskLevel.SAFE

    @classmethod
    def risk_description(cls, risk_level: str) -> str:
        return (
            "This action is low-risk and can execute immediately."
            if risk_level == RiskLevel.SAFE
            else "This action may create an external commitment or irreversible effect and needs your confirmation before it runs."
        )

    @classmethod
    def _sanitize_tool_arguments(cls, tool_arguments: dict[str, Any] | None) -> dict[str, Any]:
        if not tool_arguments:
            return {}

        sanitized: dict[str, Any] = {}
        for key, value in tool_arguments.items():
            normalized_key = str(key).lower().replace("-", "_")
            if any(secret_key in normalized_key for secret_key in cls._SECRET_KEY_FIELDS):
                continue
            sanitized[key] = value
        return sanitized

    @classmethod
    def create_pending_confirmation(
        cls,
        session: AsyncSession,
        *,
        user_id: UUID,
        requested_action: str,
        tool_name: str,
        tool_arguments: dict[str, Any] | None,
        human_readable_summary: str,
        risk_level: str,
        ttl_seconds: int = 900,
    ) -> Confirmation:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        sanitized_arguments = cls._sanitize_tool_arguments(tool_arguments)
        confirmation = Confirmation(
            user_id=user_id,
            requested_action=requested_action,
            tool_name=tool_name,
            tool_arguments=sanitized_arguments,
            human_readable_summary=human_readable_summary,
            risk_level=risk_level,
            status="pending",
            expires_at=expires_at,
        )
        session.add(confirmation)
        session.add(
            WorkspaceActivity(
                user_id=user_id,
                action="confirmation_created",
                title="Confirmation created",
                detail=human_readable_summary,
                metadata_={
                    "confirmation_id": str(confirmation.id),
                    "risk_level": risk_level,
                    "tool_name": tool_name,
                    "summary": human_readable_summary,
                },
            )
        )
        return confirmation

    @classmethod
    async def confirm(cls, session: AsyncSession, *, confirmation_id: UUID, user_id: UUID) -> Confirmation:
        stmt = select(Confirmation).where(Confirmation.id == confirmation_id)
        confirmation = (await session.execute(stmt)).scalar_one_or_none()
        if not confirmation:
            raise ValueError("Confirmation not found")
        if confirmation.user_id != user_id:
            raise PermissionError("This confirmation does not belong to you")
        if confirmation.status not in {"pending"}:
            raise ValueError("This confirmation is no longer pending")
        if confirmation.expires_at <= datetime.now(timezone.utc):
            confirmation.status = "expired"
            await cls.record_activity(session, confirmation, "confirmation_expired")
            raise TimeoutError("This confirmation has expired")
        confirmation.status = "confirmed"
        await cls.record_activity(session, confirmation, "confirmation_confirmed")
        return confirmation

    @classmethod
    async def reject(cls, session: AsyncSession, *, confirmation_id: UUID, user_id: UUID) -> Confirmation:
        stmt = select(Confirmation).where(Confirmation.id == confirmation_id)
        confirmation = (await session.execute(stmt)).scalar_one_or_none()
        if not confirmation:
            raise ValueError("Confirmation not found")
        if confirmation.user_id != user_id:
            raise PermissionError("This confirmation does not belong to you")
        if confirmation.status not in {"pending", "confirmed"}:
            raise ValueError("This confirmation is not pending")
        confirmation.status = "rejected"
        await cls.record_activity(session, confirmation, "confirmation_rejected")
        return confirmation

    @classmethod
    async def execute_pending(cls, session: AsyncSession, *, confirmation_id: UUID, user_id: UUID) -> Confirmation:
        stmt = select(Confirmation).where(Confirmation.id == confirmation_id)
        confirmation = (await session.execute(stmt)).scalar_one_or_none()
        if not confirmation:
            raise ValueError("Confirmation not found")
        if confirmation.user_id != user_id:
            raise PermissionError("This confirmation does not belong to you")
        if confirmation.status == "executed":
            raise ValueError("This action has already been executed")
        if confirmation.status not in {"pending", "confirmed"}:
            raise ValueError("This confirmation cannot be executed")
        if confirmation.expires_at <= datetime.now(timezone.utc):
            confirmation.status = "expired"
            await cls.record_activity(session, confirmation, "confirmation_expired")
            raise TimeoutError("This confirmation has expired")
        confirmation.status = "executed"
        await cls.record_activity(session, confirmation, "confirmation_executed")
        return confirmation

    @classmethod
    async def pending_for_user(cls, session: AsyncSession, user_id: UUID) -> list[Confirmation]:
        stmt = select(Confirmation).where(Confirmation.user_id == user_id, Confirmation.status == "pending").order_by(Confirmation.created_at.desc())
        return list((await session.execute(stmt)).scalars().all())

    @classmethod
    async def mark_expired(cls, session: AsyncSession, confirmation: Confirmation) -> None:
        if confirmation.status == "pending" and confirmation.expires_at <= datetime.now(timezone.utc):
            confirmation.status = "expired"
            await cls.record_activity(session, confirmation, "confirmation_expired")

    @staticmethod
    async def record_activity(session: AsyncSession, confirmation: Confirmation, action: str) -> None:
        metadata = {
            "confirmation_id": str(confirmation.id),
            "risk_level": confirmation.risk_level,
            "tool_name": confirmation.tool_name,
            "summary": confirmation.human_readable_summary,
        }
        session.add(
            WorkspaceActivity(
                user_id=confirmation.user_id,
                action=action,
                title=f"Confirmation {action}",
                detail=confirmation.human_readable_summary,
                metadata_=metadata,
            )
        )
