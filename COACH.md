# Synzept V2 Coach

## Overview

The Coach is a mock-driven proactive guidance layer that helps users stay aligned with their missions without overwhelming them.

## Backend

- Service: backend/app/services/coach/service.py
- Mock data: backend/app/services/coach/mock_data.py
- API routes:
  - GET /api/internal/coach/morning
  - GET /api/internal/coach/midday
  - GET /api/internal/coach/evening
  - GET /api/internal/coach/weekly
  - GET /api/internal/coach/state

## UI

- Morning brief
- Midday check-in
- Evening reflection
- Weekly coaching summary
- Low-volume coaching experience with snooze/disable messaging

## Tests

- Backend tests validate that the coach returns each brief and the coaching state.
