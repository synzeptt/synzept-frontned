import time
from collections import defaultdict
from hashlib import sha256
from typing import Any

from redis import asyncio as redis_async
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.security import decode_token
from app.core.reliability import safe_error_message

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Shared Redis rate limiter with a deliberate local-development fallback."""

    _INCREMENT_SCRIPT = """
    local count = redis.call('INCR', KEYS[1])
    if count == 1 then
        redis.call('EXPIRE', KEYS[1], ARGV[1])
    end
    return count
    """

    def __init__(self, app, redis_client: Any | None = None) -> None:
        super().__init__(app)
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._redis = redis_client
        if self._redis is None and settings.redis_url:
            self._redis = redis_async.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )

    @property
    def uses_redis(self) -> bool:
        return self._redis is not None

    @property
    def requires_redis(self) -> bool:
        return getattr(settings, "environment", "development") == "production"

    def _identity(self, request: Request, client: str) -> str:
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            try:
                payload = decode_token(authorization[7:].strip(), "access")
                subject = str(payload["sub"])
                return f"user:{subject}:ip:{client}"
            except Exception:
                pass
        return f"ip:{client}"

    def _key(self, identity: str) -> str:
        digest = sha256(identity.encode()).hexdigest()
        return f"synzept:rate-limit:v1:{digest}"

    def _allow_local(self, key: str, now: float) -> bool:
        window = self._hits[key]
        self._hits[key] = [timestamp for timestamp in window if now - timestamp < settings.rate_limit_window_seconds]
        if len(self._hits[key]) >= settings.rate_limit_per_minute:
            return False
        self._hits[key].append(now)
        return True

    async def _allow(self, key: str, now: float) -> bool:
        if self._redis is None:
            if self.requires_redis:
                raise RuntimeError("rate limiter Redis is unavailable")
            return self._allow_local(key, now)
        count = await self._redis.eval(
            self._INCREMENT_SCRIPT,
            1,
            key,
            settings.rate_limit_window_seconds,
        )
        return int(count) <= settings.rate_limit_per_minute

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in ("/health", "/health/ready", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        now = time.time()
        key = self._key(self._identity(request, client))
        try:
            allowed = await self._allow(key, now)
        except Exception:
            if self.uses_redis or self.requires_redis:
                return JSONResponse(
                    status_code=503,
                    content={"error": "rate_limit_unavailable", "message": "Request protection is temporarily unavailable. Please try again."},
                )
            allowed = False

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error": "rate_limit", "message": safe_error_message("rate_limit")},
            )

        return await call_next(request)


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject unexpectedly large API requests before they reach handlers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        try:
            too_large = bool(content_length and int(content_length) > settings.request_max_body_bytes)
        except ValueError:
            too_large = True
        if too_large:
            return JSONResponse(
                status_code=413,
                content={"error": "request_too_large", "message": "That request is too large to process safely."},
            )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Small production-safe header layer for API responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        if settings.environment == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response
