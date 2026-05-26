# ADR-0005: Enforce a V1 Completion Boundary

## Status

Accepted

## Context

Synzept can expand into many directions: agents, automation, integrations, collaboration, voice, mobile, and enterprise systems. Building these before the core memory-driven workspace is stable would increase complexity, delay launch, and dilute product identity.

## Decision

Synzept V1 is limited to the systems defined in `docs/product/v1_completion_boundary.md`:

- authentication
- chat
- memory
- projects
- notes
- tasks
- daily experience
- AI orchestration
- stability layer
- feedback and analytics

Future-only systems are explicitly deferred until after V1 launch.

## Tradeoffs

Benefits:

- protects launch focus
- reduces architecture churn
- keeps implementation testable
- preserves calm product identity
- prioritizes memory and continuity quality

Costs:

- some attractive integrations and automation features must wait
- post-launch roadmap decisions require discipline and user evidence

## Rejected Alternatives

- build a broad AI productivity suite before launch
- prioritize autonomous agents before memory continuity is reliable
- add social/team features before single-user workflows are stable

## Future Considerations

After launch, revisit deferred systems using retention data, memory quality feedback, and observed workflow friction.
