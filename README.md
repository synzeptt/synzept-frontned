# Synzept V1

Synzept is a personal AI operating system, not a chatbot. It provides persistent memory, context-aware assistance, and continuity across conversations, projects, notes, and tasks.

## Development Order

All development must follow the mandatory phase order in [docs/IMPLEMENTATION_ORDER.md](docs/IMPLEMENTATION_ORDER.md) and the engineering rules in [docs/ENGINEERING_RULES.md](docs/ENGINEERING_RULES.md). New work must verify its dependencies, reuse existing systems, and stabilize earlier layers before expanding later ones.

## Architecture

| Layer | Stack |
|-------|-------|
| Frontend | Next.js, TypeScript, Tailwind |
| Backend | Python, FastAPI, async SQLAlchemy |
| Database | PostgreSQL + pgvector |
| AI | OpenAI + Anthropic |
| Deploy | Vercel, Railway, Supabase |

## Backend Modules

- `chat` - conversations and messages
- `memory` - short-term and long-term memory
- `retrieval` - semantic search and ranking
- `tasks` - task management
- `orchestration` - response pipeline
- `launch` - waitlist and controlled invite access
- `feedback` - issue, suggestion, response, and memory-quality signals
- `analytics` - usefulness metrics for retention, continuity, projects, tasks, and onboarding

## Quick Start

### 1. Database

Run Alembic migrations from `backend/`, or run the SQL in `backend/migrations/001_initial.sql` for the base Supabase schema.

```bash
cd backend
alembic upgrade head
```

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd ..
cp .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`.

## API Overview

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/chat` | Send message |
| `POST /api/v1/chat/stream` | Stream response tokens |
| `GET /api/v1/dashboard` | Briefing, priorities, and context |
| `POST /api/v1/launch/waitlist` | Join early access waitlist |
| `POST /api/v1/launch/invites` | Create controlled access invite |
| `POST /api/v1/feedback` | Submit issue, suggestion, or response rating |
| `POST /api/v1/feedback/memory` | Flag memory relevance or context quality |
| `POST /api/v1/analytics/event` | Track usefulness-oriented usage event |
| `GET /api/v1/analytics/usefulness` | 30-day usefulness and retention signals |
| CRUD | `/projects`, `/notes`, `/tasks`, `/memories`, `/conversations` |

## Launch Posture

V1 is focused early access: stable onboarding, memory continuity, controlled invites, lightweight feedback, support guidance, and usefulness analytics before advanced automation or feature expansion.
