# Synzept V2 Opportunity Engine

## Architecture

- OpportunityEngineService ranks and surfaces the highest-leverage opportunities from mock context.
- Opportunity score breakdown supports impact, confidence, and urgency weighting.
- Opportunity history and feedback endpoints allow future UI interactions to persist.

## Services

- OpportunityEngineService: ranks opportunities, stores history, and returns score breakdowns.

## Data models

- OpportunityOut: title, category, summary, impact, effort, urgency, confidence, score, expectedOutcome, suggestedFirstAction, evidence, source.
- OpportunityFeedbackOut: captures accept/dismiss/snooze feedback.
- OpportunityScoreBreakdownOut: returns the sub-scores behind the overall score.

## Mock data

- Mock opportunities cover growth, productivity, learning, and startup themes.
- Mock history captures accepted and dismissed outcomes.

## APIs

- GET /api/internal/opportunities
- GET /api/internal/opportunities/history
- POST /api/internal/opportunities/feedback
- GET /api/internal/opportunities/score-breakdown/{opportunity_id}

## UI components

- Opportunities page with top opportunities, why-it-matters summary, suggested first action, and accept/snooze/dismiss actions.

## Example opportunities

- Double down on onboarding clarity
- Turn daily habits into momentum
- Surface the most useful memories earlier

## Tests

- Backend test validates ranking, history, and score breakdown output.
