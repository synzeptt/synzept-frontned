# Synzept S1 Architecture and Product Plan

## Product contract

Synzept S1 is the continuity layer over the existing Synzept platform: **an AI that knows you, remembers your life and work, and helps you move forward.** V1/V2 remain the system of record. S1 provides one stable read model and a simpler product surface; it does not fork authentication, memory, billing, projects, tasks, open loops, Daily Brief, notifications, or mobile infrastructure.

## Architecture

```text
Web / Android WebView
        |
        v
GET /api/v1/s1/context
        |
        +-- DashboardAggregationService (Home / Personal OS)
        +-- ContinueContextService (return restoration)
        +-- DailyBriefPhase8Service (today)
        +-- UserUnderstandingService (Knows You)
        |
        v
Existing SQLAlchemy models -> PostgreSQL/Supabase or local SQLite
```

`GET /api/v1/s1/context` is an additive backend-for-frontend contract. It returns Home, Continue, Daily Brief, Knows You, context-source counts, and client capability flags in one authenticated response. Existing V1/V2 APIs remain supported for fallback and detailed mutations.

### Ownership and trust

- Every source service scopes reads and writes by the authenticated `user.id`.
- User-entered and learned understanding remain distinguishable through `source` and `confidence`.
- Users can inspect, edit, and delete understanding in **Settings -> Synzept Knows You**.
- S1 does not copy data into a parallel profile, preventing drift between V1/V2 and S1.
- PostgreSQL production must use the existing ownership/RLS deployment procedure; SQLite remains a development path only.

## UI redesign

Primary navigation is limited to:

1. Home
2. Chat
3. Daily Brief
4. Settings

Secondary systems—projects, tasks, notes, memory explorer, open-loop management, timeline, relationship graph, and Pro intelligence—remain routable from contextual links and Settings but no longer compete for primary navigation.

### Home

Home answers five questions within one scan:

- What is my mission?
- What am I focused on?
- What happened last time?
- Which open loops need attention?
- What should I do next?

The primary action writes the full continuation prompt into the existing Chat handoff and opens Chat in one click.

### Chat

Chat retains streaming, conversation history, project association, retry/offline handling, and memory orchestration. The empty state and composer use **“What would you like to continue?”** and expose the continuity panel so the user can see mission, focus, projects, open loops, and recent threads being used.

### Daily Brief

The existing Phase 8 Daily Brief is the canonical S1 brief. It exposes what changed, what matters, open loops, recommended action, and today’s focus. “Continue Today’s Work” hands a structured brief to Chat.

### Synzept Knows You

The existing `user_understanding` model remains canonical and now covers:

- Personal: about me, interests, habits, preferences
- Professional: job, startup, projects, responsibilities
- Goals: short-term, long-term, missions
- Relationships: important people, commitments
- Learning: what the user wants to learn
- Current situation: current focus, current struggles, open loops

Automatic learned understanding, decision memory, recent priorities, project context, and memory-timeline items remain visible rather than being hidden behind the profile.

## Backend implementation plan

1. Keep V1/V2 services authoritative and test their ownership rules.
2. Use `S1ContextService` as the stable composition boundary for web and mobile.
3. Move expensive duplicate aggregation behind short-lived per-user caching only after production traces show a need; never cache across users.
4. Trigger understanding extraction through the existing memory/learning pipeline after conversations and workspace activity.
5. Keep Daily Brief generation idempotent per user/date and refresh explicit.
6. Add observability for S1 context latency, source counts, empty-profile rate, continuation clicks, and brief-to-chat conversion.

## Database plan

No S1 migration is required for this release. `user_understanding.category` is already a flexible string, while projects, tasks, memories, conversations, open loops, Daily Brief snapshots, subscriptions, and notification settings already exist.

Before a future typed taxonomy migration:

- measure actual category use;
- add aliases/backfill before constraints;
- preserve unknown legacy categories;
- deploy readers before writers and writers before constraints;
- retain rollback compatibility for at least one release.

## API plan

### New stable read endpoint

`GET /api/v1/s1/context`

Returns:

- `home`: greeting, mission, focus, last-time activity, open loops, recommendation
- `continue_context`: one-click continuation cards and prompts
- `daily_brief`: canonical Daily Brief snapshot
- `knows_you`: normalized user-understanding profile
- `context_sources`: counts for transparency and diagnostics
- `capabilities`: client feature discovery

### Existing mutation endpoints retained

- understanding CRUD: `/api/v2/user-understanding`
- chat and streaming: `/api/v1/chat`, `/api/v1/chat/stream`
- Daily Brief refresh: `/api/daily-brief/refresh`
- open-loop actions: `/api/open-loops-engine/*`
- billing/payments, notifications, projects, tasks, notes, conversations, and memories remain unchanged

## Mobile plan

The Android application continues to ship the responsive Next.js application through the existing mobile wrapper. S1 adds a four-item safe-area-aware bottom navigation, uses the same bearer-token session and API contract, and retains shared billing, notifications, memory, and sync behavior.

Release validation must cover Android back navigation, keyboard/composer resize, offline recovery, token refresh after backgrounding, deep links to Chat and Daily Brief, notification handoff, and responsive layouts at 360px and 390px widths.

## Pro boundaries

Free S1 includes core understanding, bounded memory, Home, Chat, base Daily Brief, and Continue. Existing billing entitlement `is_pro` gates deeper understanding, unlimited memory policy, advanced briefs, weekly reviews, relationship intelligence, long-term goal tracking, and proactive recommendations. Entitlements must be enforced server-side as well as hidden or explained in the client.

## Success instrumentation

Primary metric: a returning user reaches a meaningful continuation action without restating context.

Supporting measures:

- return-to-continue conversion after 3, 7, and 14 days;
- median time from Home load to continuation;
- percentage of responses using memory, understanding, projects, and open loops;
- Daily Brief view-to-continue conversion;
- understanding correction/deletion rate;
- empty mission, focus, and open-loop rates;
- user-rated context relevance.
