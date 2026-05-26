import asyncio
import logging
from collections.abc import AsyncIterator

from app.core.reliability import safe_error_message
from app.services.ai.base_provider import AIStreamChunk
from app.utils.sse import format_sse

logger = logging.getLogger(__name__)


class StreamService:
    @staticmethod
    async def sse_from_chunks(chunks: AsyncIterator[AIStreamChunk]) -> AsyncIterator[str]:
        try:
            async for chunk in chunks:
                yield format_sse(chunk.event, chunk.to_sse_data())
        except asyncio.CancelledError:
            logger.info("SSE stream cancelled by client")
            raise
        except Exception as exc:
            logger.exception("SSE stream failed: %s", exc)
            yield format_sse("error", {"message": safe_error_message(getattr(exc, "code", None))})
