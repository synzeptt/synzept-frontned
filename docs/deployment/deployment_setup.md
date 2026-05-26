# Deployment Setup

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js on Vercel |
| Backend | FastAPI on Railway |
| Database | Supabase PostgreSQL + pgvector |
| Background jobs | asyncio by default, Dramatiq + Redis when durability is required |
| Storage | Supabase Storage, optional |

## Environment Variables

Shared source: `.env.example`

Backend required:

- `DATABASE_URL`
- `JWT_SECRET_KEY`

Backend recommended:

- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
- `CORS_ORIGINS`
- `ENVIRONMENT=production`
- `LOG_JSON=true`
- `INVITE_REQUIRED=true` for controlled launch
- `EARLY_ACCESS_ENABLED=true`
- `RATE_LIMIT_PER_MINUTE=120`
- `REQUEST_MAX_BODY_BYTES=1000000`
- `LLM_STREAM_START_TIMEOUT_SECONDS=12`

Frontend required:

- `NEXT_PUBLIC_API_URL`

Google auth optional:

- `GOOGLE_CLIENT_ID`
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID`

## Local Development

Backend:

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
npm install
npm run dev
```

PostgreSQL:

```bash
cd backend
docker compose up -d db
```

## Migrations

Raw SQL migrations are in `backend/migrations`.

Apply in order:

```bash
psql "$DATABASE_URL" -f backend/migrations/001_initial.sql
psql "$DATABASE_URL" -f backend/migrations/002_align_v1_models.sql
psql "$DATABASE_URL" -f backend/migrations/003_conversation_persistence.sql
psql "$DATABASE_URL" -f backend/migrations/004_memory_retrieval_foundation.sql
psql "$DATABASE_URL" -f backend/migrations/005_workspace_continuity.sql
```

## Health Checks

| Endpoint | Purpose |
|---|---|
| `GET /health` | liveness and database status |
| `GET /health/ready` | readiness, returns 503 if database is unavailable |
| `GET /health/diagnostics` | database, AI, retrieval, and metric diagnostics |
| `GET /health/ai` | configured AI provider availability |
| `GET /health/retrieval` | memory/retrieval schema health |
| `GET /health/metrics` | in-process V1 performance metrics |

## Railway Backend Validation

1. Set `ENVIRONMENT=production`, `LOG_JSON=true`, `DATABASE_URL`, `JWT_SECRET_KEY`, CORS origins, and at least one AI provider key.
2. Set `INVITE_REQUIRED=true` for controlled public launch.
3. Configure Railway health check to `/health/ready`.
4. Confirm `/health/diagnostics` reports database connected and migration version `005_workspace_continuity`.
5. Confirm logs do not include secrets or raw provider keys.

## Vercel Frontend Validation

1. Set `NEXT_PUBLIC_API_URL` to the Railway backend URL.
2. Set `NEXT_PUBLIC_GOOGLE_CLIENT_ID` only if Google sign-in is enabled.
3. Deploy and verify `/early-access`, `/login`, `/onboarding`, `/dashboard`, `/chat`, `/settings`, and `/help`.
4. Confirm invite-required copy appears on signup when backend requires invites.

## Supabase Validation

1. Enable `vector` extension.
2. Apply migrations in order.
3. Verify tables: `users`, `user_profiles`, `memories`, `embeddings`, `usage_events`, `feedback_items`, `waitlist_entries`, `invite_codes`.
4. Confirm indexes from `/health/retrieval`.
5. Enable automated backups before opening access.

## Monitoring

Current implementation:

- request tracing middleware
- structured logging option
- AI interaction audit table
- health endpoints

Production follow-up:

- external uptime check
- Railway/Vercel log drains
- database backup verification
- AI provider failure rate alerts
