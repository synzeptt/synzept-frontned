# Phase 6 — Daily Brief

## Files changed

- `backend/app/services/daily_brief_phase8_service.py`: bounded history and S1 mission-category support
- `backend/app/api/daily_brief_phase8.py`: history endpoint
- `src/lib/api.ts`: Daily Brief history client
- `backend/tests/test_daily_brief_phase8.py`: all five required sections and history validation

## API added

- `GET /api/daily-brief/history?limit=14` (bounded from 1 to 31)

Existing today and refresh APIs remain canonical.

## Behavior

Every brief returns what changed, what matters today, open loops requiring attention, the recommended action, and focus for today. Mission lookup recognizes both legacy and S1 categories. Daily snapshots remain unique per user/date and can now be reviewed through bounded history.

## Tests

- Context-powered generation
- Required section population
- Same-day persistence
- History ordering and bounded limit validation
- Daily Brief frontend TypeScript/lint during final build

## Deployment

Deploy backend before client. No migration is required because history uses existing per-user/date snapshots.

## Remaining tasks

- Schedule proactive morning delivery in the production notification worker.
- Measure brief-view to Continue conversion and stale-brief refresh frequency.
