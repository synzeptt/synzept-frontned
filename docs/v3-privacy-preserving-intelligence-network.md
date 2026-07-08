# Privacy-Preserving Intelligence Network

The Privacy-Preserving Intelligence Network lets Synzept improve recommendations from aggregate behavioral and decision patterns while keeping private user context isolated.

## Architecture

### Personal Intelligence

Personal Intelligence stays user-specific and private:

- User memories
- Decision history
- Goals
- Missions
- Knowledge graph
- Raw conversations
- Named people
- Exact project notes

This layer powers personalized reasoning but is never exposed to other users or copied into global pattern learning as raw content.

### Global Intelligence

Global Intelligence contains anonymous aggregates only:

- Aggregated success patterns
- Common decision sequences
- Outcome statistics
- Anonymous trend analysis

The global layer stores pattern categories, counts, buckets, and thresholded statistics. It does not contain private memories, raw conversations, names, or identifiable project text.

## Privacy Model

- Separate personalized reasoning from global pattern learning.
- Label every recommendation with personal evidence and generalized community patterns separately.
- Allow users to opt in or opt out of anonymous contribution.
- Use thresholded aggregate patterns before a global signal becomes usable.
- Store audit events describing which boundary was used.

## APIs

- `GET /api/internal/privacy-intelligence`
  Returns the full mock privacy intelligence snapshot.
- `GET /api/internal/privacy-intelligence/recommendations`
  Returns recommendations with separated evidence.
- `GET /api/internal/privacy-intelligence/global-patterns`
  Returns anonymized aggregate patterns.
- `GET /api/internal/privacy-intelligence/contribution-settings`
  Returns opt-in settings.
- `POST /api/internal/privacy-intelligence/contribution-settings`
  Updates mock opt-in or opt-out state.

## UI

The UI lives at `/privacy-network` and shows:

- Personal Intelligence versus Global Intelligence.
- Anonymous contribution controls.
- Recommendations with personal evidence separated from global patterns.
- Privacy explanations.
- Shared versus local-only signals.
- Global aggregate patterns.
- Privacy guarantees and audit trail.

## Mock Boundary

This implementation uses mock data only. It does not collect, upload, anonymize, or aggregate production user data. The contracts are shaped so a future privacy-preserving aggregation pipeline can be added behind the same API.

## Tests

`backend/tests/test_privacy_intelligence.py` verifies that layers are separated, recommendations label evidence provenance, global patterns are anonymized aggregates, opt-out is supported, and privacy guarantees prevent raw private data from entering global intelligence.
