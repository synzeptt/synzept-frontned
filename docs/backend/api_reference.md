# API Reference

Base path: `/api/v1`

Protected routes require:

```text
Authorization: Bearer <access_token>
```

## Auth

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/auth/signup` | create email/password user and issue tokens |
| `POST` | `/auth/login` | authenticate and issue tokens |
| `POST` | `/auth/google` | authenticate with Google ID token |
| `POST` | `/auth/refresh` | rotate refresh token and issue new tokens |
| `POST` | `/auth/refresh-token` | rotate refresh token and issue new tokens |
| `POST` | `/auth/logout` | revoke refresh token |
| `GET` | `/auth/me` | return current authenticated user |
| `GET` | `/auth/current-user` | return current authenticated user |
| `GET` | `/auth/profile` | return current user's profile |

## Chat

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/chat` | non-streaming AI response |
| `POST` | `/chat/stream` | streaming AI response over Server-Sent Events |

Chat request shape:

```json
{
  "message": "string",
  "conversation_id": "uuid | null",
  "project_id": "uuid | null"
}
```

Streaming events:

| Event | Payload |
|---|---|
| `meta` | conversation id, intent, status |
| `token` | streamed assistant content |
| `suggestions` | optional action suggestions |
| `done` | completion marker and conversation id |
| `error` | safe user-facing error |

## Conversations

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/conversations` | list user conversations |
| `POST` | `/conversations` | create conversation |
| `GET` | `/conversations/{id}/messages` | list conversation messages |

## Memory

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/memories` | list memories |
| `PATCH` | `/memories/{id}` | edit memory content/category/importance |
| `DELETE` | `/memories/{id}` | soft delete memory |

Memory intelligence routes also exist under `/memory` for retrieval and diagnostic workflows. Keep additions documented when route contracts stabilize.

## Organization

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/projects` | list projects |
| `POST` | `/projects` | create project |
| `GET` | `/projects/{id}` | get project |
| `GET` | `/notes` | list notes |
| `POST` | `/notes` | create note |
| `GET` | `/tasks` | list tasks, optional status filter |
| `POST` | `/tasks` | create task |
| `PATCH` | `/tasks/{id}` | update task |

## Daily and Dashboard

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/dashboard` | load workspace dashboard |
| `GET` | `/briefing` | generate briefing |
| `GET` | `/daily/today` | get today's daily experience |
| `POST` | `/daily/regenerate` | regenerate morning/evening summary |
| `POST` | `/daily/evening/close` | close day and create evening summary |

## Launch, Feedback, Analytics

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/launch/waitlist` | join waitlist |
| `POST` | `/launch/invites` | create invite |
| `POST` | `/feedback` | submit feedback |
| `POST` | `/feedback/memory` | submit memory feedback |
| `POST` | `/analytics/event` | track usage event |
| `GET` | `/analytics/usefulness` | usefulness metrics |

## Health

Health routes are not under `/api/v1`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | liveness and database status |
| `GET` | `/health/ready` | readiness |
| `GET` | `/health/diagnostics` | detailed diagnostics |
