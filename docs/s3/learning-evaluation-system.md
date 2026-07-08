# Sprint 3 Learning & Evaluation System

The Learning & Evaluation System closes the loop on Synzept recommendations. Every recommendation should eventually be compared with a real-world outcome so future reasoning can improve.

## Workflow

1. Record recommendation.
2. Record reasoning plan ID and related decision ID.
3. Record confidence and prediction.
4. Wait for outcome.
5. Compare prediction with actual result.
6. Calculate accuracy.
7. Extract lessons.
8. Update the user's Decision Profile.

## Data Model

- `Recommendation`: recommendation text, status, confidence, reasoning plan link, decision link, tags.
- `Prediction`: predicted outcome, probability, measurable signal, horizon, assumptions.
- `Outcome`: actual outcome, success flag, evidence, user feedback.
- `Evaluation`: prediction accuracy, acceptance, success, time to outcome, feedback score.
- `Lesson`: extracted lesson, applicability, confidence delta, Decision Profile update.
- `ConfidenceHistory`: confidence over time with reasons.
- `DecisionProfile`: calibration score, strengths, blind spots, recommendation preferences.

## Metrics

- Prediction accuracy
- Recommendation acceptance rate
- Recommendation success rate
- Time to outcome
- User feedback score

## Feedback

Users can mark recommendations as:

- Helpful
- Incorrect
- Outdated
- Incomplete

Feedback updates recommendation status and adds a confidence-history event.

## Integration Points

- Reasoning Engine: recommendations store `reasoningPlanId` so the evaluated outcome can be traced back to a structured plan.
- Decision Engine: recommendations can store `decisionId` so lessons can update Decision DNA and future decision recommendations.
- Intelligence Dataset Pipeline: review-gate outcomes become evidence for future approval-boundary recommendations.

## APIs

Base path: `/api/learning-evaluation`

- `GET /`: dashboard data.
- `GET /recommendations`: recommendation history.
- `POST /recommendations`: record a recommendation and prediction.
- `POST /recommendations/{recommendation_id}/outcome`: record actual outcome and create evaluation plus lesson.
- `POST /recommendations/{recommendation_id}/feedback`: record user feedback.

## UI

The internal dashboard is available at `/learning-evaluation`.

It shows:

- recommendation history
- accuracy trends
- accepted vs rejected status
- lessons learned
- confidence calibration
- Decision Profile updates

This sprint uses mock data only and does not connect to production recommendation stores.
