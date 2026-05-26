from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import json
import logging

from app.core.dependencies import get_current_user, get_db
from app.core.reliability import safe_error_message
from app.core.config import get_settings
from app.database.session import SessionLocal
from app.infrastructure.monitoring import monitor
from app.models.user import User
from app.models.feedback import UsageEvent
from app.orchestrator.pipeline import Orchestrator
from app.schemas.chat import ChatRequest, ChatResponse
from app.utils.sse import format_sse

router = APIRouter(prefix="/chat")
logger = logging.getLogger(__name__)
settings = get_settings()


@router.post("", response_model=ChatResponse)
async def send_message(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    with monitor.timed("chat.request", stream=False):
        session.add(UsageEvent(user_id=user.id, event_type="message_sent", surface="chat"))
        result = await Orchestrator(session, user.id).run(
            body.message,
            body.conversation_id,
            body.project_id,
            body.provider,
            body.model,
            body.temperature,
            body.max_tokens,
        )
    session.add(
        UsageEvent(
            user_id=user.id,
            event_type="conversation_continued" if body.conversation_id else "conversation_started",
            surface="chat",
            metadata_={"project_id": str(body.project_id) if body.project_id else None},
        )
    )
    return ChatResponse(
        conversation_id=result["conversation_id"],
        message_id=result["message_id"],
        reply=result["reply"],
        intent=result.get("intent"),
        suggestions=result.get("suggestions", []),
    )


@router.post("/stream")
async def stream_message(body: ChatRequest, user: User = Depends(get_current_user)):
    async def sse_events():
        async with SessionLocal() as session:
            started = asyncio.get_running_loop().time()
            sent_done = False
            try:
                session.add(UsageEvent(user_id=user.id, event_type="message_sent", surface="chat_stream"))
                yield format_sse("meta", {"status": "started"})
                last_emit = asyncio.get_running_loop().time()
                async for chunk in Orchestrator(session, user.id).stream(
                    body.message,
                    body.conversation_id,
                    body.project_id,
                    body.provider,
                    body.model,
                    body.temperature,
                    body.max_tokens,
                ):
                    now = asyncio.get_running_loop().time()
                    if now - last_emit > 10:
                        yield format_sse("heartbeat", {"status": "working"})
                        last_emit = now
                    try:
                        data = json.loads(chunk)
                    except json.JSONDecodeError:
                        logger.warning("Malformed stream chunk skipped")
                        continue
                    if "token" in data:
                        yield format_sse("token", {"content": data["token"]})
                    elif "provider" in data:
                        yield format_sse("provider", data["provider"])
                    elif "usage" in data:
                        yield format_sse("usage", data["usage"])
                    elif "suggestions" in data:
                        yield format_sse("suggestions", {"items": data["suggestions"]})
                    elif "intent" in data and "conversation_id" in data:
                        yield format_sse(
                            "meta",
                            {"conversation_id": data["conversation_id"], "intent": data["intent"]},
                        )
                    elif data.get("done"):
                        sent_done = True
                        session.add(
                            UsageEvent(
                                user_id=user.id,
                                event_type="conversation_continued" if body.conversation_id else "conversation_started",
                                surface="chat_stream",
                                metadata_={"project_id": str(body.project_id) if body.project_id else None},
                            )
                        )
                        yield format_sse("done", {"conversation_id": data.get("conversation_id")})
                    last_emit = asyncio.get_running_loop().time()
                await session.commit()
                monitor.record(
                    "chat.stream",
                    int((asyncio.get_running_loop().time() - started) * 1000),
                    "success" if sent_done else "partial",
                )
            except asyncio.CancelledError:
                await session.rollback()
                monitor.record(
                    "chat.stream",
                    int((asyncio.get_running_loop().time() - started) * 1000),
                    "cancelled",
                )
                logger.info("Chat stream cancelled by client", extra={"operation": "stream"})
                raise
            except Exception as exc:
                await session.rollback()
                monitor.record(
                    "chat.stream",
                    int((asyncio.get_running_loop().time() - started) * 1000),
                    "error",
                    error_code=getattr(exc, "code", exc.__class__.__name__),
                )
                logger.exception("Chat stream failed", extra={"operation": "stream", "error_code": getattr(exc, "code", None)})
                yield format_sse("error", {"message": safe_error_message(getattr(exc, "code", None))})

    return StreamingResponse(
        sse_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Stream-Heartbeat-Seconds": str(settings.llm_stream_start_timeout_seconds),
        },
    )
