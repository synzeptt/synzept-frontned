import logging

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.reliability import safe_error_message

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: str = "app_error",
        user_message: str | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        self.user_message = user_message or safe_error_message(code)
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, status_code=404, code="not_found")


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, status_code=401, code="unauthorized")


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message, status_code=403, code="forbidden")


class AIProviderError(AppError):
    def __init__(self, message: str = "AI provider unavailable") -> None:
        super().__init__(message, status_code=503, code="ai_provider_error")


class TimeoutError(AppError):
    def __init__(self, message: str = "Request timed out") -> None:
        super().__init__(message, status_code=504, code="timeout")


class RetrievalError(AppError):
    def __init__(self, message: str = "Context retrieval failed") -> None:
        super().__init__(message, status_code=206, code="retrieval_error")


class DatabaseError(AppError):
    def __init__(self, message: str = "Database unavailable") -> None:
        super().__init__(message, status_code=503, code="database_error")


async def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning(
        "application error",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "path": request.url.path,
            "status": exc.status_code,
            "error_code": exc.code,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.code, "message": exc.user_message, "request_id": getattr(request.state, "request_id", None)},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = "unauthorized" if exc.status_code == 401 else "http_error"
    message = safe_error_message(code) if code == "unauthorized" else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": code, "message": message, "request_id": getattr(request.state, "request_id", None)},
    )


async def validation_exception_handler(request: Request, exc) -> JSONResponse:
    logger.info(
        "request validation failed",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "path": request.url.path,
            "status": 422,
            "error_code": "invalid_request",
        },
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": "invalid_request",
            "message": safe_error_message("invalid_request"),
            "details": [
                {"field": ".".join(str(part) for part in err.get("loc", [])), "message": err.get("msg")}
                for err in exc.errors()[:8]
            ],
            "request_id": getattr(request.state, "request_id", None),
        },
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception(
        "database error",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "path": request.url.path,
            "status": 503,
            "error_code": "database_error",
        },
    )
    return JSONResponse(
        status_code=503,
        content={
            "error": "database_error",
            "message": safe_error_message("database_error"),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


async def database_connection_exception_handler(request: Request, exc: OSError) -> JSONResponse:
    logger.exception(
        "database connection error",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "path": request.url.path,
            "status": 503,
            "error_code": "database_error",
        },
    )
    return JSONResponse(
        status_code=503,
        content={
            "error": "database_error",
            "message": safe_error_message("database_error"),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled error",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "path": request.url.path,
            "status": 500,
            "error_code": "internal_error",
        },
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": safe_error_message("internal_error"),
            "request_id": getattr(request.state, "request_id", None),
        },
    )
