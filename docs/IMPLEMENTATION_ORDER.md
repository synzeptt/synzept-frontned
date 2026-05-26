# Synzept Implementation Order

This document is mandatory for all Synzept development from this point forward.

Synzept is built layer by layer. Do not add disconnected features, duplicate systems, or jump ahead of unfinished foundations. Stability, continuity, and integration are higher priority than speed.

All implementation must also follow [ENGINEERING_RULES.md](ENGINEERING_RULES.md).

## Development Rule

Before implementing any feature:

1. Verify its phase dependencies already exist.
2. Verify the current architecture supports it.
3. Verify there is no duplicate module, service, store, route, or model.
4. Reuse existing modules before creating new ones.
5. Add or update tests at the level touched by the change.

If a dependency is unstable, stop and stabilize that dependency first.

## Phase 1: Foundation

Build and verify:

- project structure
- environment configuration
- database connection
- FastAPI application setup
- frontend application setup
- authentication system
- base UI system
- API communication layer

Exit criteria:

- backend starts
- frontend builds
- env examples are accurate
- authenticated API requests work
- base UI renders without hydration/layout instability

## Phase 2: Database And Core Models

Build and verify:

- SQLAlchemy models
- migrations
- relationships
- repositories/services
- user model
- conversation model
- project model
- task model
- memory model

Exit criteria:

- migrations apply and roll back safely
- relationships load correctly
- async database access works
- services own domain logic instead of route handlers duplicating it

## Phase 3: Chat System

Build and verify:

- chat UI
- conversation creation
- message persistence
- streaming responses
- AI provider integration
- chat history retrieval

Exit criteria:

- streaming starts quickly and remains smooth
- conversations persist correctly
- no duplicated chat state exists
- retry/cancel behavior preserves user intent

## Phase 4: Memory System

Build and verify:

- memory extraction
- embedding generation
- semantic retrieval
- memory ranking
- context assembly
- memory persistence

Exit criteria:

- retrieval relevance is tested
- memory injection is accurate and bounded
- prompts use only trusted context
- continuity survives session changes

## Phase 5: Project System

Build and verify:

- projects
- notes
- project memory
- linked conversations
- project summaries

Exit criteria:

- project context persists between sessions
- retrieval quality is project-aware
- notes and conversations link to projects without duplicate state

## Phase 6: Task And Organization System

Build and verify:

- tasks
- priorities
- reminders
- AI task suggestions
- dashboard summaries

Exit criteria:

- tasks remain continuous across chat/dashboard views
- dashboard data is accurate
- AI suggestions do not create work without explicit user intent

## Phase 7: Daily Intelligence System

Build and verify:

- daily briefings
- summaries
- continuity engine
- proactive suggestions
- context restoration

Exit criteria:

- summaries are useful and grounded
- recommendations feel relevant
- proactive behavior is calm and non-intrusive

## Phase 8: Stability And Polish

Build and verify:

- loading states
- retries
- fallback systems
- error handling
- memory editing
- performance optimization
- responsive UI
- production monitoring

Exit criteria:

- application stability is verified
- frontend interactions are smooth
- retrieval latency is measured
- streaming reliability is tested

## Phase 9: Public Launch Preparation

Build and verify:

- onboarding polish
- feedback system
- analytics
- waitlist/invite flow
- documentation
- privacy controls
- deployment pipelines

Exit criteria:

- onboarding quality is verified
- memory trustworthiness is verified
- production stability is verified
- retention usability is verified

## Required Verification

After each implementation phase, run the relevant subset of:

```bash
npm run lint
npm run build
python -m compileall backend\app
python -m pytest backend\tests
```

For database changes, also run from `backend/`:

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

For streaming, memory, or orchestration changes, add focused tests before moving to the next phase.

## Current Posture

The repository already contains systems across multiple phases. Future work must not expand later-phase functionality until the earlier-phase dependencies used by that work are verified and stable.

When in doubt, choose the smaller stabilization task.
