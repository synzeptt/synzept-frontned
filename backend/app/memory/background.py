"""Background memory processing — non-blocking post-response updates."""

import logging
from uuid import UUID

from app.infrastructure.jobs import JobType, enqueue

logger = logging.getLogger(__name__)


def schedule_post_response(
    *,
    user_id: UUID,
    conversation_id: UUID,
    user_message: str,
    assistant_reply: str,
    project_id: UUID | None,
) -> None:
    """Queue memory update after response completes (Dramatiq or asyncio)."""
    enqueue(
        JobType.MEMORY_POST_RESPONSE,
        user_id=user_id,
        conversation_id=conversation_id,
        user_message=user_message,
        assistant_reply=assistant_reply,
        project_id=project_id,
    )
