# Frontend Architecture Audit

## Active Frontend

The active production frontend is the root Next.js application:

- Build command: `npm run build`
- Script: `next build`
- Config: `next.config.mjs`
- App Router root: `src/app`
- Shared frontend library: `frontend`

The `frontend` directory is not an app entrypoint. It is used by active `src/app/(os)` routes through the `@frontend/*` alias.

## Inactive Frontends Removed

These duplicate app structures were inactive for the root production build and have been removed:

- `apps/web`
- `frontend-v2`
- `frontend/src/app`

They were not selected by `npm run build`, but the previous broad TypeScript include pattern still type-checked their files. That caused root production builds to fail or become misleading.

## Root Cause

The repository had multiple App Router trees:

- `src/app`: active root production app.
- `frontend/app`: shared page/component library imported by active routes, not a Next entrypoint.
- `frontend/src/app`: inactive nested route experiment.
- `frontend-v2/app`: inactive legacy V2 app tree.
- `apps/web/src/app`: inactive alternate Next app.

`npm run build` compiled the root Next app and recognized `src/app`, but `tsconfig.json` included `**/*.ts` and `**/*.tsx`. That made inactive frontends participate in root type-checking. The build failure confirmed this with a type error from `apps/web/src/app/app/chat/page.tsx`, even though `apps/web` was not the app being routed.

## Required Code Changes Made

- Removed inactive duplicate frontend app structures.
- Scoped `tsconfig.json` to active frontend code:
  - `src/**/*.ts`
  - `src/**/*.tsx`
  - `frontend/**/*.ts`
  - `frontend/**/*.tsx`
- Excluded inactive/non-frontend trees from root type-checking:
  - `apps`
  - `frontend-v2`
  - `backend`
  - `android`
  - `docs`
- Updated `.vercelignore` to keep inactive frontend structures out of deployment if they reappear.

## Production Route Expectations

The following pages are owned by `src/app` and should be emitted by the root production build:

- `/coach`
- `/life-graph`
- `/action-center`
- `/reasoning-engine`
- `/learning-evaluation`
- `/intelligence-dataset`
- `/protocol`
- `/privacy-network`

## Files Moved

No files needed to be moved. The newly added pages already lived under the active `src/app` tree.

## Files Deleted

- `apps/web/**`
- `frontend-v2/**`
- `frontend/src/app/**`

## Rule Going Forward

New production routes must be added under `src/app`. Shared UI may live under `src/components`, `src/lib`, or `frontend` when it is imported by `src/app`, but no new parallel App Router trees should be created outside `src/app`.
