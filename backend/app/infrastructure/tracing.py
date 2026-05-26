"""Request tracing — correlation IDs across logs and AI audit."""

import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

import logging

from app.core.config import get_settings
from app.infrastructure.monitoring import monitor

logger = logging.getLogger("synzept.http")
settings = get_settings()

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return _request_id.get()


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Attach a request ID and log request lifecycle."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = _request_id.set(request_id)
        request.state.request_id = request_id
        start = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = int((time.perf_counter() - start) * 1000)
            monitor.record(
                "api.request",
                duration_ms,
                "success",
                method=request.method,
                path=request.url.path,
                http_status=response.status_code,
            )
            log = logger.warning if duration_ms >= settings.slow_request_ms or response.status_code >= 500 else logger.info
            log(
                "request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            duration_ms = int((time.perf_counter() - start) * 1000)
            monitor.record("api.request", duration_ms, "error", method=request.method, path=request.url.path)
            logger.exception(
                "request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            raise
        finally:
            _request_id.reset(token)
