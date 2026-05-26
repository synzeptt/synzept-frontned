# ADR-0001: Use a Modular Monolith for V1

## Status

Accepted

## Context

Synzept needs memory, chat, retrieval, projects, tasks, onboarding, daily summaries, and AI orchestration to work together with low operational overhead.

## Decision

Use one FastAPI backend as a modular monolith. Keep module boundaries clear inside `app/api`, `app/services`, `app/orchestrator`, `app/memory`, `app/models`, and `app/infrastructure`.

## Tradeoffs

Benefits:

- simpler deployment
- simpler debugging
- shared transaction/session handling
- less duplicated orchestration logic
- faster V1 iteration

Costs:

- requires discipline to preserve boundaries
- background jobs must be kept separate from request latency

## Rejected Alternatives

- microservices for auth, memory, chat, tasks
- separate AI orchestration service
- event-driven architecture for V1

## Future Considerations

Extract background workers only when load or operational durability requires it.
