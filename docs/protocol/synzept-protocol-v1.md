# Synzept Protocol V1

The Synzept Protocol is an open, permission-based standard for representing a person's goals, knowledge, decisions, projects, preferences, and related context across applications. This phase is mock-only and does not expose production user information.

## Architecture

- Protocol manifest: versioned declaration of supported resources, principles, SDKs, sample apps, and auth flow.
- Resource service: read and permitted update surface for user-owned protocol resources.
- Permission service: scoped grants, pending requests, revocation, and status checks.
- Subscription service: app webhooks for approved change events.
- Audit service: user-visible logs for every data sharing attempt.
- Developer console: UI for inspecting schemas, mock resources, grants, subscriptions, SDK shape, and audit logs.

## Resource Types

- `profile`: minimal approved profile fields.
- `goals`: goals, status, confidence, and mission links.
- `missions`: mission state, progress, and goal links.
- `projects`: project status, priority, and decision links.
- `decisions`: meaningful decisions, confidence, status, and importance.
- `knowledge`: durable knowledge nodes and principles.
- `memories`: private memory records, only accessible with explicit category approval.
- `relationships`: people or groups, guarded by strict explicit permissions.
- `preferences`: user defaults, privacy settings, and contribution preferences.

Each resource includes `id`, `type`, `version`, `owner`, `title`, `summary`, `updatedAt`, `schemaUrl`, and typed `data`.

## Permission Model

Every app must request access by resource type and scope. Permissions are fine-grained, revocable, and auditable.

Example scopes:

- `goals:read:summary`
- `goals:read:status`
- `knowledge:write:note_link`
- `projects:write:task_link`
- `memories:read:summary`

Default posture is deny. Raw memories, named relationships, and private conversation-derived context require explicit category approval.

## REST API

Base path: `/api/protocol/v1`

- `GET /api/protocol/v1`: protocol manifest.
- `GET /api/protocol/v1/resources`: list resources.
- `GET /api/protocol/v1/resources?type=goals`: filter resources by type.
- `GET /api/protocol/v1/resources/{resource_type}/{resource_id}`: read one resource.
- `PATCH /api/protocol/v1/resources/{resource_type}/{resource_id}`: mock update when the caller has write scope.
- `GET /api/protocol/v1/permissions`: list grants.
- `POST /api/protocol/v1/permissions/request`: create a pending permission request.
- `POST /api/protocol/v1/permissions/{grant_id}/revoke`: revoke a grant.
- `GET /api/protocol/v1/subscriptions`: list subscriptions.
- `POST /api/protocol/v1/subscriptions`: create a mock subscription.
- `GET /api/protocol/v1/audit`: list data sharing audit events.

## Authentication

The proposed flow is OAuth 2.1 authorization code with PKCE.

1. App registers redirect URI and requested resource scopes.
2. User reviews every requested data category and scope.
3. Synzept issues a short-lived access token and scoped refresh token after approval.
4. Each resource read or write checks active grants.
5. Every attempt writes an audit event.
6. User can revoke any grant; future calls fail immediately.

## SDK Structure

TypeScript package: `@synzept/protocol`

- `auth`: PKCE flow helpers and token refresh.
- `resources`: typed resource reads and permitted updates.
- `permissions`: permission request and revoke helpers.
- `subscriptions`: webhook registration helpers.
- `audit`: user-visible sharing logs.

Python package: `synzept-protocol`

- Mirrors the same modules for backend and automation integrations.

## Sample Applications

- Focus Calendar: reads goal summaries and statuses to create focus blocks.
- Research Notes: links external research notes to Synzept knowledge with approval.
- Task Bridge: proposed example for creating task links from approved project summaries.

## Privacy Requirements

- No production data is connected in this implementation.
- No app receives a broad workspace token.
- Permissions are scoped by resource type and action.
- Revoked permissions must fail immediately.
- Audit logs are user visible.
- Schema evolution is additive by default and versioned by resource type.

## Test Coverage

The mock backend tests cover manifest completeness, resource filtering, permission creation, revocation, audit visibility, subscriptions, and SDK/auth metadata.
