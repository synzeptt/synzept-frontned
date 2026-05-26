# Memory System

Memory is the core Synzept differentiator. It exists to preserve continuity without forcing the user to repeat context.

## Memory Types

| Type | Purpose | Storage |
|---|---|---|
| short-term | recent conversation context | `messages` table, loaded by `ShortTermMemory` |
| long-term | durable extracted user/project context | `memories` table |
| semantic | vector-searchable snippets | `embeddings` table |
| project context | project-specific summaries and decisions | `project_context` table |
| daily context | briefings, summaries, focus continuity | `daily_summaries` table |

## Main Modules

| Module | Responsibility |
|---|---|
| `memory/context_engine.py` | assembles full context payload before AI response |
| `memory/pipeline.py` | intent -> semantic search -> rank -> select |
| `memory/semantic.py` | pgvector semantic lookup |
| `memory/scoring.py` | composite relevance scoring |
| `memory/validation.py` | filters unsafe, noisy, or low-value context |
| `memory/store.py` | memory persistence and lookup |
| `memory/background.py` | schedules post-response memory work |
| `memory/extractor.py` | extracts durable memory candidates |
| `memory/summarize.py` | summarizes conversation/context |

## Retrieval Strategy

Memory retrieval combines:

- semantic similarity from pgvector embeddings
- lexical overlap with the current query
- memory importance
- recency
- access history
- active project match
- safety and relevance validation

This avoids storing everything blindly in prompts and keeps context bounded.

## Ranking Logic

`score_memory` computes a weighted composite:

```text
semantic + lexical + importance + recency + access + project
```

Weights are defined in `memory/constants.py`. Selected memories must pass `filter_scored_memories`, which removes low-score and untrusted context before prompt assembly.

## Embedding Flow

```text
source content
  -> EmbeddingService.embed
  -> embeddings table with source_type/source_id/content/vector
  -> SemanticRetriever.search
  -> semantic score map for memory ranking
```

If embedding credentials are unavailable, semantic retrieval returns an empty hit list and the system falls back to lexical/importance/project scoring.

## Context Assembly Impact

`ContextEngine.build` assembles:

- user profile
- conversation summary
- active intent
- short-term messages
- long-term memories
- project context
- semantic snippets
- task snapshot
- daily context

The payload is passed to `PromptAssembler`. Context must remain relevant, trusted, and bounded to preserve response quality and latency.

## Memory Update Flow

After a chat response:

```text
IntelligenceOrchestrator._schedule_memory
  -> schedule_post_response
  -> background task
  -> memory extraction/summarization
  -> memories and embeddings update
```

Memory updates must not block streaming responses.
