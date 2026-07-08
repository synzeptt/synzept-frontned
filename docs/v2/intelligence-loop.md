# Synzept Intelligence Loop

The Intelligence Loop is the platform foundation for Synzept V2. Every feature should either contribute events to the loop or consume the loop's model, predictions, recommendations, action requests, or learning outcomes.

## Loop Stages

1. Observe: normalize events from conversations, missions, projects, tasks, notes, decisions, and memories.
2. Understand: update an evolving user model for goals, priorities, interests, relationships, and working patterns.
3. Predict: produce forward-looking insights with probability, confidence, risk, horizon, and supporting evidence.
4. Recommend: rank actionable recommendations by expected impact, confidence, and priority fit.
5. Act: create permission-based action requests. Meaningful actions require explicit user approval before execution.
6. Learn: record accepted, ignored, rejected, successful, and unsuccessful outcomes to improve future ranking.

## Backend Architecture

- API router: `backend/app/api/intelligence_loop.py`
- Schemas: `backend/app/schemas/intelligence_loop.py`
- Orchestrator: `backend/app/services/intelligence_loop/service.py`
- Stage services:
  - `observe.py`
  - `understand.py`
  - `predict.py`
  - `recommend.py`
  - `act.py`
  - `learn.py`
- Mock data: `backend/app/services/intelligence_loop/mock_data.py`

## APIs

- `GET /api/internal/intelligence-loop`
  Returns a full loop snapshot.
- `POST /api/internal/intelligence-loop/observe`
  Accepts one normalized event.
- `GET /api/internal/intelligence-loop/understand`
  Returns the current user model.
- `GET /api/internal/intelligence-loop/predict`
  Returns predictions.
- `GET /api/internal/intelligence-loop/recommend`
  Returns ranked recommendations.
- `POST /api/internal/intelligence-loop/act/approval`
  Records explicit approval or rejection for an action request.
- `POST /api/internal/intelligence-loop/learn`
  Records an outcome and mock learning adjustment.

## Common Event Model

Every feature should emit events with:

- `source`: conversation, mission, project, task, note, decision, memory, or feature-specific source.
- `eventType`: decision, progress, open_loop, deadline, memory, pattern, constraint, feedback, or action outcome.
- `title` and `description`
- `occurredAt`
- `actor`
- `entities`
- `signals`
- `importance`
- `urgency`
- `metadata`

## Feature Participation

- Memory Feed consumes predictions and recommendations to decide what appears first.
- Action Center consumes recommendations and emits accepted or completed action outcomes.
- Opportunity Engine contributes opportunity forecasts and consumes learning outcomes.
- Trust Engine consumes supporting evidence and confidence values.
- Life Graph contributes relationship, goal, and pattern events.
- Chat emits conversation events and can ask for approval before taking actions.

## Production Boundary

This implementation uses realistic mock data only. It does not connect to production user data, execute external actions, or contact people. The action layer records approval but never executes in mock mode.

## Tests

`backend/tests/test_intelligence_loop.py` covers normalized observation, user-model confidence, complete loop snapshots, prediction evidence, recommendation ranking, permission gating, and learning outcomes.

## UI Example

The mock console lives at `/intelligence-loop` and demonstrates how product surfaces can render the loop without production data.
