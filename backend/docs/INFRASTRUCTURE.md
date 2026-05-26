# Synzept Infrastructure Foundation

PostgreSQL (Supabase or Neon) is the **single source of truth**. No secondary databases or caching layers in V1.

## Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI on Railway |
| Frontend | Next.js on Vercel |
| Database | PostgreSQL + pgvector |
| Background jobs | asyncio (default) or Dramatiq + Redis (production) |
| Storage | Supabase Storage (optional) |

## Database schema

### Core tables

| Table | Purpose |
|-------|---------|
| `users` | Auth, preferences, onboarding |
| `user_profiles` | Intelligence profile (goals, style, routines) |
| `conversations` | Thread metadata, summaries, active intent |
| `messages` | Chat history, tokens, provider metadata |
| `memories` | Long-term extracted knowledge |
| `embeddings` | pgvector semantic index |
| `projects` | Work containers |
| `project_context` | Versioned project context entries |
| `notes` | User notes |
| `tasks` | Simple task tracking |
| `daily_summaries` | Cached daily briefings |
| `ai_interactions` | LLM audit log (latency, provider, errors) |
| `refresh_tokens` | JWT refresh rotation |

### Design principles

- UUID primary keys
- Indexed foreign keys
- `created_at` / `updated_at` on all entities
- Soft delete (`deleted_at`) where user data can be removed
- HNSW index on `embeddings.embedding` for cosine similarity

## Migrations

```bash
cd backend
alembic upgrade head
```

Revision chain: `001` → `002` → `003`

Railway: set **Release Command** to `alembic upgrade head` or run migrations in CI before deploy.

## Local development

### Option A — Docker Postgres

```bash
docker compose up -d db
```

Set in `.env`:

```
DATABASE_URL=postgresql+asyncpg://synzept:synzept@localhost:5432/synzept
```

### Option B — Supabase / Neon

Use the hosted connection string (enable pgvector in Supabase SQL editor: `create extension vector;`).

## Background processing

Heavy work runs **after** the HTTP response:

| Job | Trigger |
|-----|---------|
| `memory_post_response` | After each chat reply |
| `conversation_summarize` | Manual / scheduled |
| `daily_summary` | Scheduled / on-demand |

### Without Redis (default)

Jobs run via `asyncio.create_task` in the API process. Fine for local dev and early launch.

### With Redis (recommended for production)

```bash
REDIS_URL=redis://localhost:6379/0
docker compose --profile worker up -d
```

Worker process:

```bash
dramatiq app.workers.tasks --processes 1 --threads 2
```

## Logging

- Development: human-readable logs
- Production: set `LOG_JSON=true` for structured JSON
- Every request gets `X-Request-ID` for tracing
- AI calls logged to `ai_interactions` table

## Health checks

| Endpoint | Use |
|----------|-----|
| `GET /health` | Liveness + DB status |
| `GET /health/ready` | Readiness (503 if DB down) |

## Backups (Supabase / Neon)

**Supabase:** Dashboard → Database → Backups (daily on Pro). Enable Point-in-Time Recovery for production.

**Neon:** Automatic backups with branch-based restore.

**Recommendation:**

1. Enable provider automated backups before public launch
2. Export critical tables periodically if required for compliance
3. Never store secrets in the database

## Deployment

### Railway (backend)

- `railway.toml` runs `uvicorn app.main:app`
- Set all env vars from `.env.example`
- Add release command: `alembic upgrade head`
- Optional second service: Dramatiq worker with `REDIS_URL`

### Vercel (frontend)

- `NEXT_PUBLIC_API_URL` → Railway API URL

## Environment variables

See `backend/.env.example` for the full list.

Required: `DATABASE_URL`, `JWT_SECRET_KEY`  
Recommended: `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`  
Production: `LOG_JSON=true`, `REDIS_URL`, `ENVIRONMENT=production`

## What we intentionally avoid in V1

- Multiple databases
- Redis caching layer
- Microservices
- Premature sharding
- Complex message queues beyond Dramatiq

Add Redis only when background job durability or rate limiting at scale requires it.
