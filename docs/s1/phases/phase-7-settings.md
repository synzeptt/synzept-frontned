# Phase 7 — Settings

## Files changed

- `src/app/(os)/settings/page.tsx`: editable profile and data-management hub
- `backend/app/api/v1/auth.py`: profile update and export routes
- `backend/app/services/user_profile_service.py`: synchronized account/profile edits
- `backend/app/services/account_data_export_service.py`: safe portable export
- `backend/app/schemas/auth.py`, `src/lib/api.ts`: contracts
- `backend/tests/test_settings_data_management.py`: profile/export safety coverage

## APIs added

- `PATCH /api/v1/auth/profile`
- `GET /api/v1/auth/export`

## Settings coverage

- Profile: display name and stable summary
- Subscription: current entitlement, upgrade, and billing management
- Notifications: frequency, time, event types, email, and push settings
- Data management: inspect understanding, manage memories, JSON export, and permanent account deletion

The export deliberately excludes password hashes, refresh tokens, reset tokens, and payment secrets.

## Tests

- Profile/account synchronization
- Portable export includes user-owned understanding and memory
- Secret exclusion
- Existing notification, billing, auth, and account-deletion tests
- Frontend lint/TypeScript and final production build

## Deployment

Deploy backend before web. No migration is required. Export is generated on demand under the authenticated user boundary.

## Remaining tasks

- Add asynchronous archive generation if individual accounts exceed practical JSON response size.
- Add provider-level push token registration for native notifications when the mobile wrapper adopts native push.
