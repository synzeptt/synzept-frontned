# Phase 5 — Continue System

## Files changed

- `backend/app/schemas/continue_context.py`: first-class return fields
- `backend/app/services/continue_context_service.py`: personalized Welcome Back contract and prompts
- `backend/app/services/continuity_mode_service.py`: general current-work action instead of product-specific startup copy
- `src/lib/api.ts`: Continue contract fields
- `backend/tests/test_continuity_mode.py`: personalized return-system coverage

## API changes

`GET /api/v1/continue/context` now additionally returns:

- `last_activity`
- `open_loops`
- `suggested_next_action`

Existing cards and context-source counts remain backward compatible.

## Behavior

The return experience says Welcome Back, restores last activity and open loops, recommends the next action, and hands the complete context to Chat with one click. No prompt assumes the user is building Synzept or a startup.

## Tests

- Personalized headline and current focus
- Return contract fields
- Product-agnostic continuation prompt
- Existing continuity-mode restoration and S1 context tests

## Deployment

Deploy backend before web. The added JSON fields are backward compatible and require no migration.

## Remaining tasks

- Measure return-to-continue conversion after 3, 7, and 14 days.
- Tune last-activity ranking from real return sessions.
