# Synzept Memory & Context Intelligence

## Four memory layers

| Layer | Module | Purpose |
|-------|--------|---------|
| **Short-term** | `short_term.py` | Recent messages + `active_intent`; intelligent trim |
| **Long-term** | `long_term.py` + `extractor.py` | Durable facts only; dedup; importance; categories |
| **Project** | `project_memory.py` | Notes, tasks, memories, threads; semantic enrich |
| **Semantic** | `semantic.py` | pgvector similarity (memories, notes, tasks) |

## User context graph

`user_context.py` synthesizes top memories into `users.profile_summary` after each durable extraction.

## Retrieval pipeline

```
User Input → IntentAnalyzer → SemanticRetriever → MemoryScoring → filter_relevant → ContextEngine → PromptBuilder
```

## Post-response (async)

`background.schedule_post_response()` runs memory extraction without blocking the HTTP/SSE response.

## API

- `GET /api/v1/memory/retrieve?q=...` — ranked memories + semantic hits
- `GET /api/v1/memory/context/preview?q=...&conversation_id=...` — assembled context debug

## Migration

```bash
alembic upgrade head  # applies 002_memory_intelligence
```
