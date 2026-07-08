# Synzept V2 Time Machine

## Overview

The Time Machine is a mock-driven reflection experience for exploring personal history, turning points, and growth patterns.

## Backend

- Schema: time_machine.py
- Service: time_machine_service.py
- Mock data: time_machine_mock_data.py
- API routes:
  - GET /api/internal/time-machine/journey
  - GET /api/internal/time-machine/turning-points
  - GET /api/internal/time-machine/reflections
  - GET /api/internal/time-machine/compare
  - GET /api/internal/time-machine/search

## UI

- Journey view with timeline navigation and filtering
- Turning points highlighting major shifts
- Reflection engine with evidence-backed insights
- Compare mode for before/after views
- Search through time

## Tests

- Backend tests validate that the service returns journey, turning point, reflection, comparison, and search data.
