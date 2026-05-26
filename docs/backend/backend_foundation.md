# Backend Foundation

This document records the approved Synzept backend foundation. It covers initialization only. Authentication, AI providers, memory logic, retrieval logic, and frontend integration are outside this foundation scope.

## Runtime

- Python 3.12+
- FastAPI
- Pydantic v2
- Async SQLAlchemy
- PostgreSQL with asyncpg
- Alembic migrations

## Required Structure

```text
backend/app
  api/
  core/
  database/
  models/
  schemas/
  services/
  memory/
  retrieval/
  orchestrator/
  tasks/
  prompts/
  utils/
```

The current repository contains this structure. Later-phase modules already exist, but foundation work must not duplicate them.

## Foundation Responsibilities

| Area | Owner | Responsibility |
|---|---|---|
| App startup | `app/main.py` | create FastAPI app, register middleware, exception handlers, router, health endpoints |
| Settings | `app/core/config.py` | environment-driven configuration through Pydantic settings |
| Logging | `app/core/logging.py` | structured JSON logs in production, readable logs in development |
| Database base | `app/database/base.py` | declarative SQLAlchemy base |
| Database session | `app/database/session.py` | async engine, sessionmaker, transaction lifecycle |
| Migrations | `backend/alembic` | Alembic environment and versioned migrations |
| API routing | `app/api/v1/router.py` | versioned API router mounted under `/api/v1` |
| Health | `app/main.py`, `app/infrastructure/database.py` | liveness/readiness and database diagnostics |

## Startup Flow

```text
uvicorn app.main:app
  -> load Settings from environment/.env
  -> configure FastAPI app
  -> lifespan calls setup_logging
  -> register CORS, tracing, rate limiting
  -> register exception handlers
  -> mount /api/v1 router
  -> expose /health, /health/ready, /health/diagnostics
```

## Database Flow

```text
get_settings().database_url
  -> create_async_engine
  -> SessionLocal
  -> get_db_session dependency
  -> route/service receives AsyncSession
```

Database sessions commit after successful dependency use and roll back on exceptions.

## Migration Flow

Alembic reads `DATABASE_URL` through `app/core/config.py` in `backend/alembic/env.py`.

Commands:

```bash
cd backend
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

From the repository root, use:

```bash
python -m alembic -c backend/alembic.ini upgrade head
```

## Startup Instructions

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

If PostgreSQL is not running, `/health` returns `degraded` with `database: unavailable`. This is expected for local foundation checks without a database.

## Architecture Constraints

- Do not create a second FastAPI app entry point.
- Do not create another database session manager.
- Do not call PostgreSQL outside the async SQLAlchemy session pattern.
- Do not add auth, AI, memory, retrieval, or frontend integration while working on foundation-only scope.
- Keep startup, config, logging, database, and routing responsibilities separated.
