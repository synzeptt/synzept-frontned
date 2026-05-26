# Synzept Backend

Production-ready FastAPI modular monolith.

## Structure

```
app/
  api/           # REST routes, middleware
  core/          # config, security, exceptions, dependencies
  infrastructure/# logging, tracing, jobs, DB health
  database/      # SQLAlchemy base, session, mixins
  models/        # ORM models (UUID, soft delete, indexes)
  workers/       # Dramatiq background tasks (optional Redis)
  schemas/       # Pydantic v2 validation
  services/      # auth, chat, AI providers, embeddings
  memory/        # store, retrieve, rank, summarize
  retrieval/     # semantic search, context assembly
  orchestrator/  # response pipeline
  tasks/         # task domain service
  prompts/       # prompt templates and builder
  utils/         # retry, SSE, text helpers
alembic/         # database migrations
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Local Postgres (Docker)

```bash
docker compose up -d db
# DATABASE_URL=postgresql+asyncpg://synzept:synzept@localhost:5432/synzept
```

See [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) for deployment, backups, and background workers.

## Auth

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/auth/signup` | Register |
| `POST /api/v1/auth/login` | Login |
| `POST /api/v1/auth/refresh` | Refresh tokens |
| `GET /api/v1/auth/me` | Current user |

Protected routes require `Authorization: Bearer <access_token>`.

## Streaming

`POST /api/v1/chat/stream` returns **Server-Sent Events**:

- `event: meta` — conversation metadata
- `event: token` — streamed content chunks
- `event: done` — completion
- `event: error` — failure

## AI providers

`LLMRouter` supports OpenAI and Anthropic with retries (tenacity) and automatic fallback.
