# Database Schema

PostgreSQL with pgvector is the single source of truth for V1.

## Core Tables

| Table | Purpose |
|---|---|
| `users` | auth identity, preferences, onboarding, profile summary |
| `user_profiles` | goals, work style, communication preferences, routines |
| `refresh_tokens` | refresh token rotation and revocation |
| `conversations` | chat thread metadata, project link, summaries, active intent |
| `messages` | persisted user/assistant/system messages |
| `projects` | work containers |
| `project_context` | versioned summaries, decisions, project context |
| `notes` | user notes linked optionally to projects |
| `tasks` | simple task tracking and priorities |
| `memories` | durable long-term context |
| `embeddings` | pgvector vectors for semantic retrieval |
| `daily_summaries` | morning/evening continuity summaries |
| `feedback_items` | user feedback and response ratings |
| `memory_feedback` | memory relevance/correction feedback |
| `usage_events` | product analytics events |
| `waitlist_entries` | early access waitlist |
| `invite_codes` | invite-based access control |
| `ai_interactions` | provider/model/status/latency audit log |

## Authentication Tables

`users` includes:

- UUID `id`
- unique `email`
- `password_hash` for the bcrypt hash
- `is_active`
- `is_verified`
- `created_at`
- `updated_at`
- `deleted_at`

`password_hash` is the existing persisted column name. The ORM exposes `hashed_password` as a compatibility alias for V1 auth terminology without duplicating stored password data.

`user_profiles` includes:

- `user_id`
- `display_name`
- `onboarding_completed`
- `communication_style`
- `timezone`
- `profile_metadata`
- goals and preference metadata used by later intelligence systems

## Relationships

- `users` owns conversations, projects, notes, tasks, memories, user profile, refresh tokens, daily summaries.
- `conversations` owns messages and may link to a project.
- `projects` own notes, tasks, memories, conversations, and project context.
- `memories` may link to conversations, projects, and embeddings.
- `messages` may link to embeddings.
- `ai_interactions` may link to user, conversation, and message.

## Indexing Strategy

Indexes prioritize:

- user-scoped reads
- project-scoped reads
- active/non-deleted filtering
- status and priority filtering
- semantic vector search
- token lookup and revocation

Vector search uses pgvector over `embeddings.embedding` with cosine distance.

## Migration Strategy

Current raw SQL migrations live in `backend/migrations`.

| Migration | Purpose |
|---|---|
| `001_initial.sql` | initial users, conversations, messages, projects, tasks, notes, memories, embeddings |
| `002_align_v1_models.sql` | aligns the database with the current SQLAlchemy model surface |

`002_align_v1_models.sql` is idempotent and records application in `schema_migrations`.

Alembic migrations live in `backend/alembic/versions`; current head is `007_auth_profile_foundation.py`.

## Validation Requirement

For database changes, run against a real PostgreSQL + pgvector instance:

```bash
psql "$DATABASE_URL" -f backend/migrations/001_initial.sql
psql "$DATABASE_URL" -f backend/migrations/002_align_v1_models.sql
```

Current local limitation: this machine does not have Docker or `psql`, so live migration execution remains pending.
