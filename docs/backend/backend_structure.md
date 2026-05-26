# Backend Structure

The backend is an async-first FastAPI modular monolith.

## Directory Responsibilities

| Directory | Responsibility |
|---|---|
| `app/api/v1` | HTTP routes and route-level request/response wiring |
| `app/core` | settings, security, exceptions, dependency injection, reliability helpers |
| `app/database` | SQLAlchemy base, engine, session lifecycle, mixins |
| `app/models` | ORM models mapped to PostgreSQL tables |
| `app/schemas` | Pydantic request and response contracts |
| `app/services` | domain services, auth, chat, AI providers, embeddings |
| `app/orchestrator` | central AI response pipeline |
| `app/memory` | memory extraction, retrieval, scoring, context assembly |
| `app/retrieval` | semantic retrieval compatibility helpers |
| `app/daily` | daily briefing and summary context |
| `app/tasks` | task domain service |
| `app/infrastructure` | database health, tracing, jobs, backups |
| `app/workers` | background job broker and task definitions |

## Core App Initialization

`app/main.py` owns:

- FastAPI app creation
- lifespan setup
- CORS middleware
- tracing middleware
- rate limiting middleware
- exception handlers
- API router inclusion
- health endpoints

## Database Access

`app/database/session.py` owns the async SQLAlchemy engine and `SessionLocal`.

Routes should receive sessions through `app/core/dependencies.py`. Services receive the active `AsyncSession`; they should not create unrelated sessions unless they own a streaming lifecycle that outlives route dependency scope.

## Auth

Auth responsibilities are split as:

- routes: `app/api/v1/auth.py`
- JWT/password helpers: `app/core/security.py`
- email/password auth: `app/services/auth_service.py`
- Google auth: `app/services/google_auth_service.py`
- dependency enforcement: `app/core/dependencies.py`

Protected endpoints use `get_current_user`.

Detailed auth flow is documented in `docs/backend/authentication.md`.

## Architecture Rules

- Business logic belongs in services, not route handlers.
- AI provider calls go through `LLMRouter`.
- Prompt and orchestration logic stays in `app/orchestrator` and `app/prompts`.
- Memory retrieval goes through `ContextEngine` or `MemoryRetrievalPipeline`.
- Do not introduce a second database access pattern.
