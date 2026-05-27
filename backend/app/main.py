from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sqlalchemy.exc import SQLAlchemyError

from app.api.middleware import BodySizeLimitMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import (
    AppError,
    app_exception_handler,
    database_connection_exception_handler,
    database_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler as request_validation_exception_handler,
)
from app.core.logging import setup_logging
from app.infrastructure.database import check_database, database_diagnostics, retrieval_diagnostics
from app.infrastructure.monitoring import monitor
from app.services.ai.provider_registry import ProviderRegistry
from app.infrastructure.tracing import RequestTracingMiddleware
from app.database.session import initialize_local_database

settings = get_settings()

CORS_ORIGINS = [
    "http://localhost:3000",
    "https://app.synzept.com",
]
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    await initialize_local_database()
    yield


app = FastAPI(
    title="Synzept API",
    description="Synzept backend - continuity workspace foundation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestTracingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request, exc: RequestValidationError):
    return await request_validation_exception_handler(_request, exc)


app.add_exception_handler(AppError, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(OSError, database_connection_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(api_router)


@app.get("/health")
async def health():
    db = await database_diagnostics()
    db_ok = bool(db["connected"])
    return {
        "status": "ok" if db_ok else "degraded",
        "service": "synzept-backend",
        "environment": settings.environment,
        "database": "connected" if db_ok else "unavailable",
        "migration_version": db.get("migration_version"),
        "background_worker": "redis" if settings.use_background_worker else "asyncio",
    }


@app.get("/health/diagnostics")
async def diagnostics():
    db = await database_diagnostics()
    return {
        "service": "synzept-backend",
        "environment": settings.environment,
        "database": db,
        "ai": ProviderRegistry().availability(),
        "retrieval": await retrieval_diagnostics(),
        "metrics": monitor.snapshot(),
        "background_worker": "redis" if settings.use_background_worker else "asyncio",
    }


@app.get("/health/ready")
async def readiness():
    if not await check_database():
        return JSONResponse(status_code=503, content={"ready": False, "database": "unavailable"})
    ai = ProviderRegistry().availability()
    return {"ready": True, "ai_available": ai["available"], "migration_version": (await database_diagnostics()).get("migration_version")}


@app.get("/health/ai")
async def ai_health():
    status = ProviderRegistry().availability()
    code = 200 if status["available"] else 503
    return JSONResponse(status_code=code, content=status)


@app.get("/health/retrieval")
async def retrieval_health():
    status = await retrieval_diagnostics()
    code = 200 if status["memories_table"] else 503
    return JSONResponse(status_code=code, content=status)


@app.get("/health/metrics")
async def metrics_health():
    return monitor.snapshot()
