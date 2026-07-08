# Synzept V2 10-Minute Wow Experience

## Overview

The 10-Minute Wow experience is a mock-first onboarding flow that helps a new user quickly understand why Synzept is different.

## Backend

- Service: backend/app/services/onboarding_wow_service.py
- Schema: backend/app/schemas/onboarding_wow.py
- API routes:
  - GET /api/internal/onboarding-wow/start
  - POST /api/internal/onboarding-wow/advance
  - POST /api/internal/onboarding-wow/approve

## UI

- Welcome screen
- Smart onboarding interview
- AI reasoning stage
- Results screen with mission, Daily OS, Action Center, life graph preview, insights, and next action

## Tests

- Backend tests validate the initial onboarding wow flow and generated insights.
