# Phase 3 — Home

## Files changed

- `backend/app/services/s1_home_service.py`: fast Home read model
- `backend/app/api/v1/s1.py`, `backend/app/schemas/s1.py`: Home API contract
- `frontend/app/dashboard-page.tsx`, `src/lib/api.ts`: responsive Home client and Continue handoff
- `backend/tests/test_s1_home.py`: Knows You and new-user empty-state coverage

## API added

- `GET /api/v1/s1/home`

## Behavior

Home reads mission and current focus directly from Synzept Knows You, joins only open tasks and project loops, and returns a ready-to-use continuation prompt. It deliberately does not generate a Daily Brief or load the larger S1 bundle, keeping first paint fast.

The screen contains only Mission, Current Focus, Open Loops, Suggested Next Action, and Continue Working. It is responsive by default through the existing mobile shell and safe-area navigation.

## Deployment

Deploy backend before the web client. No migration is needed. Existing dashboard and full S1 context routes remain available as fallback infrastructure.
