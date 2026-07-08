# Synzept V2 Personal Knowledge Model

## Overview

The Personal Knowledge Model is the structured understanding layer that represents the user's identity, goals, work style, strengths, growth areas, relationships, and knowledge.

## Backend

- Service: PersonalKnowledgeModelService
- Mock data source: pkm_mock_data.py
- API: GET /api/internal/pkm

## UI

- My Model page displays the model across identity, goals, work style, strengths, growth areas, and a learning timeline.

## Confidence system

Each attribute includes a confidence score, evidence, last updated timestamp, and source so the model can evolve gradually without overwriting high-confidence understanding.

## Tests

- Backend test validates that the model is returned with expected domains and timeline data.
