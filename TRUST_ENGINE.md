# Synzept V2 Trust Engine

## Overview

The Trust Engine provides explainable and reviewable recommendations for important AI decisions.

## Backend

- Schema: trust_engine.py
- Service: trust_engine_service.py
- Mock data: trust_engine_mock_data.py
- Routes:
  - GET /api/internal/trust-engine
  - POST /api/internal/trust-engine/feedback

## UI

- Recommendation cards with confidence and rationale
- Evidence panel with supporting context
- Missing information and assumptions panels
- Feedback actions for helpful, incorrect, incomplete, or needs-more-context signals

## Tests

- Backend tests validate that recommendations and feedback acknowledgement are returned.
