# Phase 2 — Synzept Knows You

## Files changed

- `backend/app/services/user_understanding_service.py`: S1 taxonomy, coverage, memory-to-understanding learning, correction protection
- `backend/app/api/v2/user_understanding.py`: coverage and sync endpoints
- `backend/app/schemas/user_understanding.py`: coverage/sync contracts
- `backend/app/workers/runner.py`: automatic understanding updates after conversation-memory extraction
- `src/app/(os)/knows-you/page.tsx`: complete editable taxonomy and learning coverage controls
- `src/lib/api.ts`: S1 understanding client contracts
- `backend/tests/test_knows_you_phase1.py`: persistence, learning, de-duplication, and correction tests

## APIs added

- `GET /api/v2/user-understanding/coverage`
- `POST /api/v2/user-understanding/sync`

Existing list/create/update/delete APIs remain unchanged.

## Database

No migration is required. The existing owned `user_understanding` rows and flexible category field support the complete S1 taxonomy. Automatic learning stores provenance through `source=learned`, confidence, and `learned_at`.

## Behavior

- Conversation memory extraction automatically promotes durable identity, interest, habit, preference, work, project, goal, skill, priority, plan, and commitment signals into the visible profile.
- Exact signals are de-duplicated.
- Editing an automatically learned item turns it into a user-owned correction with full confidence.
- User corrections take precedence over future automatic signals with the same category label.
- Coverage reports which of the 19 core S1 categories are populated, including distinct Company and Startup context.

## Deployment

Deploy the backend worker and API before the web client. Existing workers and Redis/in-process job execution remain compatible. No database operation or backfill is required; optionally call the sync endpoint once per active user to promote existing memories.

## Remaining tasks

- Observe learned-item quality with real users and tune category extraction thresholds.
- Add contradiction/merge review when two high-confidence facts disagree.
- Validate PostgreSQL RLS with the production database role as described in the S1 deployment guide.
