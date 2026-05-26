# ADR-0002: Use PostgreSQL and pgvector as the V1 Source of Truth

## Status

Accepted

## Context

Synzept needs relational persistence and semantic retrieval. V1 should avoid multiple databases and reduce operational complexity.

## Decision

Use PostgreSQL for application data and pgvector for embeddings.

## Tradeoffs

Benefits:

- one durable data store
- relational integrity for users, projects, conversations, tasks, and memories
- vector retrieval without introducing a separate vector database
- easier backups and migration discipline

Costs:

- vector search performance must be monitored as data grows
- pgvector extension must be enabled in each environment

## Rejected Alternatives

- standalone vector database for V1
- document database for memory
- Redis as source of truth

## Future Considerations

Consider a dedicated vector store only if pgvector latency or scale becomes a measured bottleneck.
