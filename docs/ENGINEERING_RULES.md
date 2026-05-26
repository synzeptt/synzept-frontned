# Engineering Rules

This document mirrors the active engineering rules in `docs/ENGINEERING_RULES.md` and adds the current reporting and documentation requirements.

## Required Process

- Inspect the codebase before creating files.
- Reuse existing modules before adding new ones.
- Preserve single ownership for each responsibility.
- Build working functionality first.
- Verify integration after changes.
- Update documentation when architecture, APIs, database, memory, retrieval, orchestration, or deployment behavior changes.

## Reporting Format

Completed implementation updates must include:

1. Objective
2. Files Created
3. Files Modified
4. Functionality Implemented
5. Integration Points
6. Dependencies
7. Testing Status
8. Known Issues
9. Next Recommended Step

## Duplication Rules

Do not introduce:

- a second auth system
- a second AI provider layer
- a second memory pipeline
- a second retrieval/ranking path
- a second frontend API client
- a second database access pattern

## Documentation Sync

Documentation is part of the implementation. An undocumented architecture change is incomplete.

Required docs live under:

- `docs/architecture`
- `docs/backend`
- `docs/frontend`
- `docs/memory`
- `docs/retrieval`
- `docs/orchestrator`
- `docs/database`
- `docs/deployment`
- `docs/product`
- `docs/decisions`

## Verification Commands

Run the relevant subset:

```bash
npm run lint
npm run build
python -m compileall backend\app
python -m pytest backend\tests
```

For database changes, validate migrations on PostgreSQL + pgvector.
