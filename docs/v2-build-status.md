# Synzept V2 Build Status Audit

Audit date: 2026-06-02

## Audit Scope

This report audits the current repository state, including modified and untracked V2 files. It does not assume that the presence of code, a migration file, or a compiled route proves production readiness.

Two database states must be kept separate:

- Local runtime: `backend/.env` points to SQLite. The local `backend/synzept.db` is at Alembic head `017` and contains the V2 tables.
- Supabase: PostgreSQL/RLS scripts exist in `backend/migrations/006_user_understanding_rls.sql` through `backend/migrations/012_workspace_system_rls.sql`, but this checkout has no configured `SUPABASE_URL` or `SUPABASE_SERVICE_KEY`. No evidence in the repository proves that these scripts have been applied to a live Supabase project.

All existing V2 API endpoints use the backend's custom bearer-token authentication through `get_current_user`. The Supabase RLS scripts use `auth.uid()`. The custom application JWT is not forwarded to PostgreSQL as a Supabase Auth context, so the RLS execution model is not yet proven compatible with the backend connection path.

## Summary

| Feature | Overall Status | Frontend | Backend | Local Database | Supabase Integration | Authentication | RLS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Synzept Knows You | Partial | Exists | Exists | Tables Created | Missing: SQL prepared only | Protected | Missing in runtime; SQL prepared |
| Daily Brief | Partial | Exists | Exists | Tables Created | Missing: SQL prepared only | Protected | Missing in runtime; SQL prepared |
| Project Intelligence | Partial | Exists | Exists | Tables Created | Missing: SQL prepared only | Protected | Missing in runtime; SQL prepared |
| Timeline | Partial | Partially Built | Partially Built | Tables Created | Missing: SQL prepared only | Protected | Missing in runtime; SQL prepared |
| Learning Engine | Partial | Exists | Exists | Tables Created | Missing: SQL prepared only | Protected | Missing in runtime; SQL prepared |
| Relationship Graph | Not Started | Not Started | Not Started | Missing | Missing | Missing | Missing |

No requested V2 system is complete against the full checklist because Supabase deployment and RLS behavior have not been connected and verified.

## Synzept Knows You

Status: **Partial**

### Frontend

Exists. The `/knows-you` route renders editable personal, professional, goals, preferences, and learned-insight sections from `frontend-v2/app/knows-you/page.tsx`.

### Backend

Exists. `backend/app/api/v2/user_understanding.py` provides authenticated list, create, patch, and delete endpoints backed by `UserUnderstandingService`.

### Database

Tables Created locally: `user_understanding`.

Supabase table creation SQL exists in `backend/migrations/006_user_understanding_rls.sql`, but live deployment is unverified.

### Security

- Supabase Integration: Missing. SQL prepared only.
- Authentication: Protected. Every endpoint requires `get_current_user`.
- Row Level Security: Missing in the audited SQLite runtime. Supabase RLS policies are prepared but not proven applied or compatible with custom JWT authentication.

### CRUD Operations

| Operation | Status |
| --- | --- |
| Create | Exists |
| Read | Exists |
| Update | Exists |
| Delete | Exists |

### Missing Work

- Connect and validate the Supabase/PostgreSQL deployment path.
- Prove RLS behavior with the actual backend database role and authentication model.
- Add endpoint/service tests specifically covering user-understanding CRUD and cross-user isolation.

### Next Actions

Treat this as the first production-hardening candidate because its application slice is already complete locally.

## Daily Brief

Status: **Partial**

### Frontend

Exists. The `/daily-brief` route loads today's brief and exposes a refresh action from `frontend-v2/app/daily-brief/page.tsx`.

### Backend

Exists. `backend/app/api/v2/daily_brief.py` provides authenticated read and refresh endpoints. `DailyBriefService` builds and persists one snapshot per user per date from understanding, projects, tasks, conversations, memories, and project open loops.

### Database

Tables Created locally: `daily_briefs`.

Supabase table creation SQL exists in `backend/migrations/007_daily_briefs_rls.sql`, but live deployment is unverified.

### Security

- Supabase Integration: Missing. SQL prepared only.
- Authentication: Protected.
- Row Level Security: Missing in the audited SQLite runtime. Supabase RLS policies are prepared but unverified.

### CRUD Operations

| Operation | Status |
| --- | --- |
| Create | Exists internally when today's brief is requested |
| Read | Exists |
| Update | Partial: refresh deletes and regenerates today's snapshot |
| Delete | Missing as a user-facing operation |

### Missing Work

- Decide whether snapshot history, explicit deletion, and date-based browsing are product requirements.
- Add tests for generation, refresh, same-day uniqueness, and user isolation.
- Validate PostgreSQL behavior for concurrent refresh requests.

### Next Actions

Keep the current feature scope, then harden persistence and test coverage before adding more brief intelligence.

## Project Intelligence

Status: **Partial**

### Frontend

Exists. Existing project detail routing now renders `frontend-v2/app/projects/project-intelligence-page.tsx`. The page supports summary, focus, next-step and status editing; decision creation/resolution; open-loop creation/closure; and related activity, conversation, and memory views.

### Backend

Exists. `backend/app/api/v2/project_intelligence.py` provides authenticated page reads, intelligence updates, decision creation/updates, and open-loop creation/updates. The service lazily creates an intelligence record for an owned project.

### Database

Tables Created locally:

- `project_intelligence`
- `project_decisions`
- `project_open_loops`

Supabase table creation SQL exists in `backend/migrations/008_project_intelligence_rls.sql`, but live deployment is unverified.

### Security

- Supabase Integration: Missing. SQL prepared only.
- Authentication: Protected.
- Row Level Security: Missing in the audited SQLite runtime. Owner policies are prepared for Supabase but unverified.

### CRUD Operations

| Resource | Create | Read | Update | Delete |
| --- | --- | --- | --- | --- |
| Project intelligence | Exists lazily | Exists | Exists | Missing |
| Decisions | Exists | Exists | Exists, including resolve | Missing |
| Open loops | Exists | Exists | Exists, including close | Missing |

### Missing Work

- Add delete or archive semantics if decisions and loops must be removable rather than only resolved or closed.
- Add direct tests for lazy record creation, ownership isolation, and each mutation.
- Add frontend error handling for decision and open-loop mutations.

### Next Actions

Harden the existing feature before extending its intelligence model.

## Timeline

Status: **Partial**

### Frontend

Partially Built. `/timeline` exists, but `frontend-v2/app/timeline/page.tsx` is a placeholder and does not call the backend.

The older dashboard also renders a separate V1 continuity timeline from daily snapshots. That is not the dedicated V2 activity timeline.

### Backend

Partially Built. `GET /api/v2/workspace/timeline` exists in `backend/app/api/v2/workspace.py`. `WorkspaceActivityService` records project, note, goal, milestone, and task activity through the newer workspace paths and selected V1 paths.

### Database

Tables Created locally: `workspace_activities`.

Supabase table creation SQL exists in `backend/migrations/012_workspace_system_rls.sql`, but live deployment is unverified.

### Security

- Supabase Integration: Missing. SQL prepared only.
- Authentication: Protected.
- Row Level Security: Missing in the audited SQLite runtime. Supabase RLS policy is prepared but unverified.

### CRUD Operations

| Operation | Status |
| --- | --- |
| Create | Partial: internal activity recording exists for selected mutations |
| Read | Exists in backend |
| Update | Missing |
| Delete | Missing |

### Missing Work

- Build the timeline page against `GET /api/v2/workspace/timeline`.
- Define event coverage: conversations, memories, Daily Brief changes, Learning Engine actions, and direct database mutations are not comprehensively represented.
- Decide whether immutable ledger semantics are intentional; if so, document why update and delete are not offered.
- Add pagination or cursor support for long-lived workspaces.

### Next Actions

This is the clearest next feature completion target after database hardening because backend storage and read APIs already exist.

## Learning Engine

Status: **Partial**

### Frontend

Exists. `/learning-engine` displays observations, suggestions, approved understanding, controls for analyze/accept/edit/ignore, learning enable/pause settings, and history deletion.

### Backend

Exists. `backend/app/api/v2/learning_engine.py` and `LearningEngineService` implement approval-first analysis. Accepted suggestions create visible `user_understanding` rows rather than silently changing the profile.

### Database

Tables Created locally:

- `learning_observations`
- `learning_suggestions`
- `user_understanding.confidence`
- `user_understanding.learned_at`

Supabase SQL exists in `backend/migrations/009_learning_engine_rls.sql`, but live deployment is unverified.

### Security

- Supabase Integration: Missing. SQL prepared only.
- Authentication: Protected.
- Row Level Security: Missing in the audited SQLite runtime. Supabase RLS policies are prepared but unverified.

### CRUD Operations

| Resource | Create | Read | Update | Delete |
| --- | --- | --- | --- | --- |
| Observations | Exists through analysis | Exists | Missing | Exists through clear history |
| Suggestions | Exists through analysis | Exists | Exists through edit, accept, and ignore | Exists through clear history only |
| Approved understanding | Exists through accept | Exists | Exists through Synzept Knows You | Exists through Synzept Knows You |

### Missing Work

- Add focused tests for analyze, accept, edit, ignore, settings, history deletion, and cross-user isolation.
- Fix the frontend error state: if initial loading fails while `engine` is null, the page continues rendering the skeleton instead of the error.
- Review observation growth and retention limits before production use.

### Next Actions

Fix the initial-load error state and validate the full approval flow against PostgreSQL.

## Relationship Graph

Status: **Not Started**

### Frontend

Not Started. No Relationship Graph route, component, or visualization exists.

### Backend

Not Started as a V2 feature. `backend/app/memory/user_context.py` contains an older lightweight `UserContextGraph` profile-summary helper, and memory categories include `relationships`, but neither is a relationship-graph system.

### Database

Missing. No V2 graph node, edge, relationship, or graph-specific table exists.

### Security

- Supabase Integration: Missing.
- Authentication: Missing because there is no feature API.
- Row Level Security: Missing.

### CRUD Operations

| Operation | Status |
| --- | --- |
| Create | Missing |
| Read | Missing |
| Update | Missing |
| Delete | Missing |

### Missing Work

- Define product scope before implementation: graph entities, relationship types, provenance, user editing, visualization, and privacy model.
- Design database ownership and RLS policies before creating UI.

### Next Actions

Do not start implementation until the existing V2 database path is production-ready and Timeline is completed.

## Additional Review

### Duplicate Code

- V1 and V2 APIs overlap for projects, notes, memory, daily experience, and brief generation. This creates two mutation paths that can drift in behavior and activity-ledger coverage.
- `WorkspaceService` and V1 project/note routes both record workspace activities manually. Centralizing event recording would reduce missed events and duplicate records.
- V1 dashboard continuity timeline and V2 workspace activity timeline are separate concepts with similar user-facing names. They need explicit naming or consolidation.

### Unused Components

- `src/components/layout/sidebar.tsx` appears unused. The active OS layout re-exports `frontend/components/layout/workspace-shell.tsx`, which implements its own sidebar.
- `frontend-v2` is wired into active routes through re-export files under `src/app/(os)`, but the parallel directory layout should be documented so it is not mistaken for an unused prototype.

### Security Concerns

- Supabase RLS is not active in local SQLite and has not been proven in a live PostgreSQL environment.
- The RLS scripts depend on `auth.uid()`, while the application validates its own JWT in FastAPI and uses SQLAlchemy sessions. Decide whether the backend uses a bypass role and enforces ownership itself, or whether requests establish a Supabase-compatible database auth context. Test the chosen model.
- The frontend stores access and refresh tokens in JavaScript-readable local storage and cookies. This increases exposure if an XSS issue occurs. Prefer server-set `HttpOnly` refresh cookies for a production deployment.
- Generated database and bytecode artifacts are present in the worktree. Remove generated artifacts from version control and keep secrets confined to ignored env files.

### Database Issues

- There are two migration tracks: Alembic revisions `011` through `017` and manually applied Supabase SQL migrations `006` through `012`. They need an explicit source of truth and a release procedure.
- Deployment documentation still stops at `backend/migrations/005_workspace_continuity.sql` and expects migration version `005_workspace_continuity`. It does not instruct operators to apply the V2 Supabase scripts.
- The local database is at Alembic head `017`, but all audited V2 feature tables are empty in this checkout. Structural presence is verified; real-user data behavior is not.
- Live PostgreSQL execution remains unverified on this machine.

### Scalability Concerns

- `WorkspaceService.get_workspace()` aggregates projects, goals, tasks, notes, memories, insights, recommendations, and timeline data in one request without workspace-level pagination.
- Workspace search uses wildcard `ILIKE` queries and JSON-to-string matching. Add PostgreSQL indexes or a search strategy before large workspaces.
- Learning analysis loads all conversations, projects, briefs, and user-authored understanding rows, then stores observations without a retention policy. Add bounded analysis windows and cleanup rules.
- The dashboard requests V1 dashboard data, V2 workspace aggregation, and V2 proactive intelligence in parallel. Review duplicated database work before scaling.
- Timeline reads have a limit but no cursor pagination.

### Technical Debt

- Add direct tests for Synzept Knows You, Daily Brief, Project Intelligence, and Learning Engine. Current V2-focused tests cover goals, memory profiles, proactive intelligence, and workspace behavior more strongly than the named V2 surfaces.
- Fix visible mojibake such as `Â·` and `â€”` in frontend and backend text.
- Configure `pytest-asyncio` loop scope explicitly to remove the deprecation warning.
- Keep full-repository lint practical by excluding `backend/venv`; targeted lint for `src`, `frontend`, and `frontend-v2` passes.

## Verification Performed

- Confirmed local database URL scheme is SQLite.
- Confirmed `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are not configured locally.
- Confirmed local Alembic revision is `017 (head)`.
- Confirmed local V2 table presence and zero-row state in `backend/synzept.db`.
- Ran `backend\venv\Scripts\python.exe -m pytest backend/tests -q`: `87 passed`.
- Ran `npx eslint src frontend frontend-v2`: passed.
- Ran `npm run build`: passed, including `/knows-you`, `/daily-brief`, `/projects/[id]`, `/timeline`, and `/learning-engine`.

## Completed Features

None of the requested V2 systems are fully complete against the full frontend, backend, database, Supabase integration, authentication, RLS, and CRUD checklist.

## Partial Features

- Synzept Knows You
- Daily Brief
- Project Intelligence
- Timeline
- Learning Engine

## Not Started

- Relationship Graph

## Recommended Next Build

Do not add another V2 product feature yet.

First, make the V2 persistence path production-ready:

1. Choose one migration source of truth and update deployment documentation through the V2 schema.
2. Connect a staging Supabase PostgreSQL database.
3. Resolve the custom JWT versus `auth.uid()` RLS model and run cross-user isolation tests.
4. Add direct tests for Synzept Knows You, Daily Brief, Project Intelligence, and Learning Engine.
5. Complete the Timeline frontend using the existing workspace activity endpoint.

After those steps, Relationship Graph can be designed against a stable security and data model.
