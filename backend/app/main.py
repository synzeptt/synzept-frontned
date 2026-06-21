from contextlib import asynccontextmanager
import asyncio
from contextlib import suppress

from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sqlalchemy.exc import SQLAlchemyError

from app.api import (
    billing,
    chat,
    continue_engine,
    context_engine_phase6,
    continuity_assistant_phase7,
    daily_brief_phase8,
    home,
    knows_you,
    learning_engine_phase4,
    notifications,
    open_loops_engine,
    product_analytics,
    project_intelligence_phase2,
    relationship_graph_phase5,
    timeline_phase3,
)
from app.api.middleware import BodySizeLimitMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
from app.api.v1.router import api_router
from app.api.v2.router import api_router as api_v2_router
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
from app.database.session import SessionLocal, initialize_local_database
from app.services.notification_service import NotificationService

settings = get_settings()

CORS_ORIGINS = [origin.strip().rstrip("/") for origin in settings.cors_origins.split(",") if origin.strip()]
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    await initialize_local_database()
    notification_task = asyncio.create_task(_notification_scheduler())
    try:
        yield
    finally:
        notification_task.cancel()
        with suppress(asyncio.CancelledError):
            await notification_task


async def _notification_scheduler() -> None:
    while True:
        try:
            async with SessionLocal() as session:
                await NotificationService(session).generate_for_all_users()
                await session.commit()
        except Exception:
            pass
        await asyncio.sleep(30 * 60)


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
    allow_origins=settings.cors_origin_list,
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
app.include_router(api_v2_router)
app.include_router(chat.router)
app.include_router(continue_engine.router)
app.include_router(billing.router)
app.include_router(billing.payments_router)
app.include_router(home.router)
app.include_router(knows_you.router)
app.include_router(project_intelligence_phase2.router)
app.include_router(timeline_phase3.router)
app.include_router(learning_engine_phase4.router)
app.include_router(relationship_graph_phase5.router)
app.include_router(context_engine_phase6.router)
app.include_router(continuity_assistant_phase7.router)
app.include_router(daily_brief_phase8.router)
app.include_router(open_loops_engine.router)
app.include_router(notifications.router)
app.include_router(product_analytics.router)


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
