# ADR-0004: Treat Documentation as Product Infrastructure

## Status

Accepted

## Context

Synzept includes memory, retrieval, orchestration, AI provider routing, database migrations, and frontend state. These systems will become difficult to extend safely if documentation lags implementation.

## Decision

Maintain synchronized technical documentation under `docs/`. Any architecture, database, memory, retrieval, orchestration, deployment, or major feature change must update the related document in the same implementation pass.

## Tradeoffs

Benefits:

- easier onboarding
- safer debugging
- fewer repeated architecture debates
- clearer ownership boundaries

Costs:

- implementation tasks must reserve time for documentation updates

## Rejected Alternatives

- documentation only after release
- documentation only in code comments
- informal notes outside the repository

## Future Considerations

Add API reference generation or OpenAPI exports when endpoint coverage stabilizes.
