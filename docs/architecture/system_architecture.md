# System Architecture

Synzept is a memory-driven AI workspace built as a Next.js frontend and FastAPI backend over PostgreSQL with pgvector.

## Responsibilities

| Layer | Responsibility | Primary Location |
|---|---|---|
| Frontend | UI, client state, API calls, streaming rendering | `src/app`, `src/components`, `src/stores`, `src/lib/api.ts` |
| API | HTTP routes, auth dependency wiring, request validation | `backend/app/api/v1` |
| Services | Domain operations and provider access | `backend/app/services` |
| Orchestrator | Chat intelligence pipeline and AI response flow | `backend/app/orchestrator` |
| Memory | extraction, retrieval, ranking, context assembly | `backend/app/memory` |
| Database | async SQLAlchemy models and sessions | `backend/app/database`, `backend/app/models` |
| Infrastructure | health, tracing, background jobs, backups | `backend/app/infrastructure`, `backend/app/workers` |

## Request Flow

```text
Browser
  -> src/lib/api.ts
  -> FastAPI route in backend/app/api/v1
  -> Auth dependency and AsyncSession
  -> Domain service or IntelligenceOrchestrator
  -> PostgreSQL / LLM provider / memory pipeline
  -> JSON or Server-Sent Events response
```

## Chat Intelligence Flow

```text
POST /api/v1/chat or /chat/stream
  -> ChatService creates/loads conversation and persists user message
  -> IntentClassifier classifies request
  -> ContextEngine assembles profile, short-term history, memories, project context, tasks, daily context
  -> PromptAssembler builds LLM messages
  -> LLMRouter calls OpenAI/Anthropic with fallback
  -> assistant message is persisted
  -> post-response memory update is scheduled
```

## AI Provider Architecture

`LLMRouter` is the single provider entry point. It selects the configured primary provider, tries fallback providers, tracks interactions through `AIInteractionLogger`, and supports both full completion and streaming.

No route or frontend component should call OpenAI or Anthropic directly.

## Product Filter

Architecture changes must improve at least one core pillar:

- memory
- continuity
- organization
- intelligence
- calm experience

Changes that add parallel systems, scattered provider calls, or extra UI complexity are rejected for V1.
