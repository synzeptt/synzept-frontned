# Synzept V2 Core Architecture

## Purpose

The V2 core foundation gives Synzept Knows You, Daily Brief, Project Intelligence, Timeline, Learning Engine, and Relationship Graph one shared ownership model.

Existing richer V2 fields remain available for compatibility. The canonical fields below are the stable minimum contract for future systems.

## Core Entities

| Entity | Table | Canonical Fields |
| --- | --- | --- |
| Users | `users` | Existing authenticated user rows |
| Projects | `projects` | `id`, `user_id`, `title`, `description`, `status`, `created_at`, `updated_at` |
| Goals | `goals` | `id`, `user_id`, `title`, `description`, `status`, `target_date`, `created_at` |
| Memories | `memories` | `id`, `user_id`, `memory_type`, `content`, `confidence`, `source`, `created_at` |
| Timeline Events | `timeline_events` | `id`, `user_id`, `event_type`, `title`, `description`, `importance`, `event_date` |
| Learning Signals | `learning_signals` | `id`, `user_id`, `signal_type`, `content`, `confidence`, `status` |
| Graph Nodes | `graph_nodes` | `id`, `user_id`, `node_type`, `title` |
| Graph Edges | `graph_edges` | `id`, `user_id`, `source_node_id`, `target_node_id`, `relationship_type`, `strength` |

## Services

Reusable service modules live in `backend/app/services`:

- `project_service.py`
- `goal_service.py`
- `memory_service.py`
- `timeline_service.py`
- `learning_service.py`
- `graph_service.py`

Every service scopes reads and mutations by `user_id`. Graph edges additionally require both endpoint nodes to belong to the same user.

## API Contract

Authenticated CRUD endpoints live under `/api/v2/core`:

- `/projects`
- `/goals`
- `/memories`
- `/timeline-events`
- `/learning-signals`
- `/graph/nodes`
- `/graph/edges`

Each resource exposes list, create, read, patch, and delete operations with the same route shape.

## Security

Apply `backend/migrations/013_core_architecture_foundation_rls.sql` after the earlier raw SQL migrations. It enables and forces Row Level Security for the core tables and scopes access with `auth.uid()`.

The current local development database is SQLite and cannot enforce PostgreSQL RLS. PostgreSQL validation must be run in a Supabase staging environment before production deployment.

## Local Development

SQLite startup uses `initialize_local_database()` to create new tables and add compatibility columns to an existing local database without resetting founder data. PostgreSQL releases should use Alembic revision `018` and the ordered Supabase SQL scripts.
