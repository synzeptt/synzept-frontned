# Decision Intelligence Engine Phase 1

The Decision Intelligence Engine captures, organizes, reviews, analyzes, and learns from meaningful decisions. Its purpose is not just recall; it is to improve future decision-making through evidence, outcomes, and Decision DNA.

## Architecture

- API router: `backend/app/api/decision_intelligence.py`
- Schemas: `backend/app/schemas/decision_intelligence.py`
- Service: `backend/app/services/decision_intelligence/service.py`
- Mock data: `backend/app/services/decision_intelligence/mock_data.py`
- UI data: `src/lib/decision-intelligence/`
- UI components: `src/components/decision-intelligence/`
- Pages:
  - `/decisions`
  - `/decisions/[id]`
  - `/decisions/reviews`
  - `/decisions/dna`
  - `/decisions/analytics`
- Tests: `backend/tests/test_decision_intelligence.py`

## Data Models

Decision records include title, description, importance, mission, goal, related projects, related people, alternatives considered, expected outcome, risks, confidence, current status, review state, timestamps, and supporting evidence.

The engine also models:

- Detection candidates with confidence gating.
- Review prompts and lifecycle states.
- Outcome analyses comparing expected and actual outcomes.
- Decision DNA traits with evidence and confidence.
- Future recommendations that reference applicable past decisions.
- Analytics for review backlog, prediction accuracy, success rate, and recurring risk themes.

## APIs

- `GET /api/internal/decision-intelligence`
  Returns the complete mock snapshot.
- `GET /api/internal/decision-intelligence/detect?min_confidence=0.75`
  Returns high-confidence decision suggestions only.
- `GET /api/internal/decision-intelligence/decisions`
  Returns decision records.
- `GET /api/internal/decision-intelligence/decisions/{decision_id}`
  Returns one decision record.
- `GET /api/internal/decision-intelligence/reviews`
  Returns review queue.
- `POST /api/internal/decision-intelligence/reviews/update`
  Records a mock review update.
- `GET /api/internal/decision-intelligence/outcomes`
  Returns outcome analyses.
- `GET /api/internal/decision-intelligence/dna`
  Returns Decision DNA.
- `GET /api/internal/decision-intelligence/recommendations`
  Returns future recommendations with transparent reasoning.

## Decision Detection

Phase 1 uses realistic mock detection candidates. A suggestion appears only when confidence is high enough and the item is important enough to justify a formal record. Low-signal activity is intentionally excluded.

## Review And Learning Loop

Decision reviews move through pending, accepted, rejected, completed, and outcome unknown states. Outcome analysis compares the expected and actual result, assigns prediction accuracy, and stores lessons as future reasoning evidence.

## Decision DNA

Decision DNA summarizes decision style, strengths, recurring mistakes, high-performing patterns, and blind spots. Every trait includes supporting evidence and confidence. This should eventually personalize recommendations for future choices.

## Production Boundary

This implementation uses mock data only. It does not connect to production conversations, notes, activities, memories, projects, or user data. The UI and API are production-shaped so real retrieval and persistence can be added later behind the same contracts.
