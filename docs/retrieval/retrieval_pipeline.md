# Retrieval Pipeline

Retrieval restores useful context for the current user message.

## Primary Flow

```text
query
  -> IntentAnalyzer / IntentClassifier
  -> SemanticRetriever.search
  -> MemoryStore.list_long_term
  -> semantic score map
  -> score_memory
  -> filter_scored_memories
  -> ContextPayload
```

## Strategy

The retrieval system uses hybrid ranking:

- semantic score from pgvector when embeddings are available
- lexical overlap for exact topic continuity
- importance for durable user facts and decisions
- recency for recent context
- access count for previously useful memories
- project match for workspace continuity

## Validation

`memory/validation.py` filters:

- prompt-injection-like memory content
- low-score memories
- irrelevant semantic hits
- oversized context candidates

This protects prompt quality and avoids noisy memory injection.

## Integration Points

- `ContextEngine` uses retrieval before every AI response.
- `IntelligenceOrchestrator._briefing` uses `MemoryRetrievalPipeline` for daily context.
- `MemoryRetriever` exists as a backward-compatible wrapper around `MemoryRetrievalPipeline`.
- `retrieval/search.py` provides semantic retrieval compatibility for older call sites.

## Performance Notes

- Retrieval is async through SQLAlchemy.
- Context assembly uses `asyncio.gather` for independent reads.
- The memory candidate list is bounded before ranking.
- Prompt insertion is capped by constants such as `MAX_MEMORIES_IN_CONTEXT`.

## Known Limitations

- Live PostgreSQL migration validation is pending on this machine because Docker and `psql` are unavailable.
- Semantic retrieval quality depends on embedding availability and vector index readiness.
