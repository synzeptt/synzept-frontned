# Synzept Local Development

This guide starts the Synzept V1 stack locally:

- PostgreSQL with pgvector
- FastAPI backend on `http://localhost:8000`
- Next.js frontend on `http://localhost:3000`

## 1. Prerequisites

- Python 3.12
- Node.js and npm
- PostgreSQL 16 with the `vector` extension, or Docker Desktop

The backend Docker Compose file uses `pgvector/pgvector:pg16`.

## 2. Environment Files

Backend: `backend/.env`

```env
DATABASE_URL=postgresql+asyncpg://synzept:synzept@localhost:5432/synzept
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
JWT_SECRET=local-dev-jwt-secret-change-before-production
JWT_SECRET_KEY=local-dev-jwt-secret-change-before-production
JWT_REFRESH_SECRET=local-dev-refresh-secret-change-before-production
FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000
```

Frontend: `.env.local`

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

The root `.env.local` is the active frontend env file because the Next.js app runs from the repository root.

## 3. Install Dependencies

```powershell
cd C:\Users\piyus\synzept\backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

cd C:\Users\piyus\synzept
npm install
```

## 4. Start PostgreSQL

With Docker Desktop installed:

```powershell
cd C:\Users\piyus\synzept\backend
docker compose up -d db
```

Without Docker, install PostgreSQL locally and create:

- user: `synzept`
- password: `synzept`
- database: `synzept`

Then enable pgvector:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 5. Run Migrations

```powershell
cd C:\Users\piyus\synzept\backend
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## 6. Start Backend

```powershell
cd C:\Users\piyus\synzept\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Verify:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health/ready
Invoke-WebRequest -UseBasicParsing http://localhost:8000/openapi.json
```

## 7. Start Frontend

```powershell
cd C:\Users\piyus\synzept
npm run dev
```

Verify:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:3000
Invoke-WebRequest -UseBasicParsing http://localhost:3000/login
Invoke-WebRequest -UseBasicParsing http://localhost:3000/dashboard
Invoke-WebRequest -UseBasicParsing http://localhost:3000/chat
```

## 8. Functional Verification

After PostgreSQL is running and migrations pass:

1. Sign up through `/login` or `POST /api/v1/auth/signup`.
2. Log in and confirm `/api/v1/auth/me` returns the user.
3. Open `/dashboard`, `/chat`, `/projects`, `/tasks`, and `/notes`.
4. Create a conversation and send a message.
5. Confirm `/api/v1/chat/stream` returns `text/event-stream`.
6. Create a project, note, and task.
7. Confirm dashboard continuity data updates.
8. Confirm memories persist and retrieval endpoints respond.

Streaming and embeddings require at least one real provider key in `backend/.env`.
