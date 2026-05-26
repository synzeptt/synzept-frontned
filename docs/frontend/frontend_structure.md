# Frontend Structure

The frontend is a Next.js app with minimal client state and backend-owned intelligence.

## Directory Responsibilities

| Directory | Responsibility |
|---|---|
| `src/app` | routes, layouts, page-level composition |
| `src/app/(os)` | authenticated operating-system workspace routes |
| `src/components` | reusable UI, layout, chat, auth, analytics components |
| `src/components/ui` | primitive UI components |
| `src/lib/api.ts` | single API client and streaming parser |
| `src/lib/types.ts` | shared frontend types |
| `src/stores` | Zustand client state for auth, chat, settings, workspace |

## API Integration

`src/lib/api.ts` is the single frontend API boundary. It owns:

- `NEXT_PUBLIC_API_URL`
- auth token storage
- access token refresh
- JSON requests
- streaming chat response parsing
- route-after-auth behavior

Components should not duplicate fetch logic.

## Chat UI

`src/app/(os)/chat/page.tsx` owns the chat screen. It integrates:

- `api.streamMessage`
- `api.sendMessage` fallback
- `useChatStore`
- abort/retry behavior
- online/offline state
- smooth token flushing through `requestAnimationFrame`

## UX Rules

- Keep screens calm and task-focused.
- Avoid dashboard overload.
- Avoid frontend AI orchestration.
- Keep controls predictable and responsive.
- Do not create new stores unless state ownership is clear and reusable.

## Build Verification

Required frontend checks:

```bash
npm run lint
npm run build
```
