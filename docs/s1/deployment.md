# Synzept S1 Deployment

## Pre-deploy

From the repository root:

```powershell
npm ci
npx eslint src frontend frontend-v2
npm run build
backend\venv\Scripts\python.exe -m pytest backend/tests -q
```

Confirm production environment values are configured for the existing backend and client, including the database URL, JWT secrets, AI provider, CORS origins, billing/payment credentials, email, and notification settings. Do not replace or reset the production database.

## Database

This S1 release has no new migration. Confirm the production database is already at the repository’s existing migration head before deployment:

```powershell
Set-Location backend
venv\Scripts\alembic.exe current
venv\Scripts\alembic.exe upgrade head
```

For Supabase/PostgreSQL, apply the repository’s existing ordered RLS scripts using the documented production role model. Verify ownership with two test users before exposing S1.

## Deploy order

1. Deploy the FastAPI backend.
2. Verify `/health`, `/health/ready`, and authenticated `GET /api/v1/s1/context`.
3. Deploy the Next.js web application to the existing Vercel project.
4. Verify login, Home, one-click Continue, Chat streaming, Daily Brief refresh, Settings, Knows You edits, billing, and logout.
5. Build the existing Android wrapper and publish to the internal track before staged production rollout.

## Web commands

```powershell
npm run build
npx vercel --prod
```

Use the existing automatic deployment pipeline instead when enabled; do not create a second Vercel project.

## Android commands

```powershell
Set-Location android
.\gradlew.bat clean bundleRelease
```

Upload `android/app/build/outputs/bundle/release/app-release.aab` to the existing Play Console application. Preserve the current application ID, signing key, deep-link configuration, and production web origin.

## Production smoke test

- Existing user can sign in without onboarding again.
- Home shows mission, focus, last-time context, open loops, and next action.
- Continue opens Chat with context already loaded.
- Chat sends, streams, persists, and restores a conversation.
- Daily Brief loads and refreshes once per user/day.
- Knows You reads and updates existing and new categories.
- Web and Android stay synchronized after refresh/backgrounding.
- Free/Pro billing state and payment callbacks are unchanged.
- Notifications deep-link into an authenticated S1 route.
- A second user cannot read or mutate the first user’s data.

## Rollback

Roll back the web client first, then backend if necessary. Existing clients continue using V1/V2 endpoints. Because this release has no schema migration, database rollback is neither required nor recommended.
