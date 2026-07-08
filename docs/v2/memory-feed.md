# Memory Feed

The Memory Feed is the first authenticated screen in Synzept V2. It proactively surfaces the most relevant items from a user's memory, project, relationship, and activity context without connecting to production data yet.

## Architecture

- Frontend entry point: `/dashboard` renders `MemoryFeed` through `frontend/app/dashboard-page.tsx`.
- UI components: `src/components/memory-feed/MemoryFeed.tsx` and `MemoryFeedCard.tsx`.
- Shared frontend model and mock data: `src/lib/memory-feed/types.ts`, `ranking.ts`, and `mock-data.ts`.
- Backend mock API: `GET /api/internal/memory-feed` and `POST /api/internal/memory-feed/refresh`.
- Backend service: `backend/app/services/memory_feed/service.py`.
- Backend schema: `backend/app/schemas/memory_feed.py`.

## Card Types

Supported cards include important memories, recent decisions, open loops, mission progress, relationship reminders, opportunities, AI insights, weekly reflections, achievements, and suggested next actions.

## Ranking

Each card carries five visible factors:

- Relevance: 30%
- Urgency: 25%
- Importance: 25%
- Recency: 15%
- Feedback: 5%

Pinned cards receive a small boost and remain above unpinned cards. Snoozed and archived cards are excluded from today's feed. The feed returns 5 to 7 cards to prevent overload.

## User Actions

The mock UI supports complete, snooze, pin, archive, follow-up question capture, and "why this card was shown" explanations. These actions are local state only for now and should later persist through a feedback endpoint.

## Production Integration Boundary

This implementation intentionally does not connect to production data. The next step is to replace the mock source with a memory retrieval pipeline that gathers candidate memories, decisions, tasks, relationship events, and progress signals, then passes them through the same ranking contract.

## Tests

Backend tests cover ranking size, pinned ordering, snoozed and archived filtering, and weighted score behavior in `backend/tests/test_memory_feed.py`.
