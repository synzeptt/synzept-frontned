# Synzept S1 Incremental Roadmap

## Release 1 — additive S1 foundation (implemented in this change)

- Add the authenticated `/api/v1/s1/context` composition contract.
- Keep V1/V2 APIs and database models intact.
- Simplify web and mobile navigation to Home, Chat, Daily Brief, Settings.
- Use S1 return context on Home with legacy endpoint fallback.
- Expand visible user understanding to the complete S1 taxonomy.
- Keep Chat and Daily Brief handoffs on the existing memory-aware orchestration path.

## Release 2 — production hardening

- Run all backend and frontend tests against staging PostgreSQL.
- Validate cross-user isolation and the chosen custom-JWT/RLS execution model.
- Add endpoint latency traces and per-source timing to S1 context.
- Add bounded per-user cache invalidated by chat, memory, project, task, loop, and understanding mutations.
- Add contract tests for empty, new, active, and returning users.
- Move refresh tokens to server-set HttpOnly cookies.

## Release 3 — continuous understanding

- Normalize new extraction results to the S1 category taxonomy.
- Add provenance and “why Synzept believes this” to every learned item.
- Add contradiction detection, confidence decay, merge, and correction flows.
- Add relationship commitments and learning intentions to recommendation ranking.
- Add user-controlled retention windows and export.

## Release 4 — proactive S1 Pro

- Advanced and scheduled Daily Briefs.
- Weekly review with changes, progress, risks, and decisions.
- Relationship intelligence and commitment follow-ups.
- Long-term mission and goal progress tracking.
- Proactive recommendations with explicit reason, source, and dismissal feedback.

## Safe rollout

1. Deploy the backend first; old clients ignore the additive endpoint.
2. Smoke-test authentication and `/api/v1/s1/context` for a new and existing user.
3. Deploy the web client with legacy fallback enabled.
4. Release Android through an internal track, then staged rollout.
5. Compare S1 context errors, Home load time, continuation rate, and support signals.
6. Roll back the client independently if needed; V1/V2 routes and data remain unchanged.

No data rollback is required for Release 1 because it adds no tables, columns, constraints, or destructive mutations.
