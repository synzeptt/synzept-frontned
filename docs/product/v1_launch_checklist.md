# Synzept V1 Launch Checklist

Synzept V1 should launch as focused, stable, useful, memory-driven, and continuity-first.

## Deployment

- Railway backend deployed with `ENVIRONMENT=production`.
- Vercel frontend deployed with `NEXT_PUBLIC_API_URL` pointing to Railway.
- Supabase PostgreSQL database migrated through `005_workspace_continuity`.
- `vector` extension enabled.
- `/health/ready`, `/health/ai`, `/health/retrieval`, and `/health/diagnostics` verified.
- Production logs use JSON and do not leak secrets.
- Rollback path documented in Railway and Vercel dashboards.

## Access Control

- `EARLY_ACCESS_ENABLED=true`.
- `INVITE_REQUIRED=true` for controlled public launch.
- Waitlist page accepts email, name, role, and intended use.
- Single-use invite creation verified from Settings.
- Signup with missing or invalid invite is rejected when invite-required mode is on.

## Onboarding

- New users route to onboarding after signup.
- Onboarding collects lightweight profile, goals, priorities, communication style, and optional starter workspace.
- Initial memories are generated.
- First AI interaction references user context.
- Dashboard is non-empty after completion.
- Resume behavior works after refresh or interruption.

## Memory Quality And Trust

- Users can view memories in Settings.
- Users can edit memories.
- Users can delete memories.
- Users can disable memory learning.
- Users can disable personalization.
- Memory issue feedback is available.
- Wrong memory recovery instructions are visible in Help.

## Stability

- API errors return safe user-facing messages.
- Streaming supports retry, stop, cancellation, and graceful error states.
- AI provider fallback is configured.
- Retrieval falls back when semantic retrieval fails.
- Rate limiting and request size limits are enabled.
- Frontend global error boundary is present.

## Analytics

- Onboarding completion is tracked.
- Daily active usage is tracked.
- Page views are tracked.
- Conversation, message, memory, project, task, feedback, and onboarding metrics are available.
- Analytics are lightweight and can be disabled by the user.

## Feedback And Support

- Feedback button is visible in app shell.
- Feedback supports bugs, memory issues, support, suggestions, and response quality.
- Settings support form works.
- Help page includes FAQ and recovery guidance.

## Founder Review Before Opening Access

- Complete one fresh signup with invite.
- Complete onboarding in under four minutes.
- Send five representative chat prompts.
- Confirm at least three useful memories are created.
- Edit and delete one memory.
- Create one project, task, and note.
- Confirm dashboard remains useful the next day.
- Review Railway logs for errors and slow requests.
- Review first-user feedback within 24 hours.
