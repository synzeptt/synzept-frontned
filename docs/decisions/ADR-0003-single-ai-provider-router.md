# ADR-0003: Centralize AI Provider Calls in LLMRouter

## Status

Accepted

## Context

Synzept uses AI providers for chat and streaming. Provider calls scattered across routes or frontend code would duplicate fallback, logging, retries, and safety behavior.

## Decision

All AI provider calls go through `app/services/providers/router.py`.

## Tradeoffs

Benefits:

- one fallback policy
- one logging path
- one streaming abstraction
- easier model/provider changes
- less duplicated provider code

Costs:

- all provider features must fit through the router abstraction

## Rejected Alternatives

- direct provider calls from routes
- provider calls from frontend
- separate routers per feature

## Future Considerations

Add capability-specific methods only when there is a real provider capability difference that the current interface cannot represent.
