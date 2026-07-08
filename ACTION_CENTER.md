# Synzept V2 Action Center

## Overview

The Action Center is the default Daily OS-style home surface for Synzept. It trims the experience down to the single highest-value question: what should I do next?

## Sections

- Today's Mission
- Top 3 Actions
- Avoid List
- AI Insight
- Momentum
- Open Loops
- Quick Actions

## Backend

- Mock API endpoint: GET /api/internal/action-center
- Service: ActionCenterService
- Schema: ActionCenterOut

## Frontend

- Mobile-first, whitespace-heavy interface with a focused layout.
- All content is mocked and ready for future connection to live data.

## Tests

- Backend test ensures the dashboard includes mission, three actions, insight, momentum, loops, and quick actions.
