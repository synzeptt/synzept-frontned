# Phase 4 — Context-Aware Chat

## Files changed

- `backend/app/orchestrator/context_builder.py`: full S1 understanding in model context and source diagnostics
- `backend/app/orchestrator/prompt_builder.py`: expanded explicit user-understanding prompt section
- `frontend/features/chat/chat-workspace.tsx`: visible context-ready state
- `backend/tests/test_orchestration_pipeline.py`: required-source and prompt assembly coverage

## APIs

No new route was required. Existing chat responses already return `trust_context`; it now includes `sources` booleans for memory, user understanding, goals, projects, previous conversations, and open loops.

## Behavior

- Chat automatically retrieves relevant long-term memory.
- The complete editable/learned S1 understanding profile is included, not only mission and focus.
- Active goals, projects, tasks, prior conversations, decisions, and open loops feed the prompt.
- The model is instructed to continue from supplied context before asking the user to restate it.
- The existing placeholder remains “What would you like to continue?” on web and mobile.

## Tests

- Orchestration prompt assembly and budget safeguards
- All six required S1 sources represented in diagnostics
- Streaming and non-streaming persistence/fallback tests
- Targeted frontend lint and TypeScript checks

## Deployment

Deploy the backend before the client. No migration is required. Monitor prompt-token usage and `trust_context.sources` coverage after release.

## Remaining tasks

- Tune retrieval ranking from real context-relevance feedback.
- Surface per-message memory provenance when users request “why did you use this?”
