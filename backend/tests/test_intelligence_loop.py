from app.schemas.intelligence_loop import ActionApprovalIn, LearningOutcomeIn
from app.services.intelligence_loop import IntelligenceLoopService, ObserveService, UnderstandService


def test_observe_normalizes_common_event_model():
    events = ObserveService().collect_events()

    assert len(events) >= 7
    assert {event.source for event in events} >= {"conversation", "mission", "project", "task", "note", "decision", "memory"}
    assert all(event.id and event.eventType and event.occurredAt for event in events)


def test_understand_updates_confidence_from_accumulated_evidence():
    events = ObserveService().collect_events()
    user_model = UnderstandService().update_user_model(events)

    goal = user_model.goals[0]
    assert goal.label == "Launch Synzept V2"
    assert goal.confidence > 0.45
    assert goal.evidence


def test_snapshot_contains_all_six_loop_stages():
    snapshot = IntelligenceLoopService().snapshot()

    assert snapshot.events
    assert snapshot.userModel.goals
    assert snapshot.predictions
    assert snapshot.recommendations
    assert snapshot.actionRequests
    assert snapshot.learningOutcomes
    assert snapshot.loopHealth["status"] == "mock_ready"


def test_predictions_include_confidence_and_supporting_evidence():
    predictions = IntelligenceLoopService().snapshot().predictions

    assert all(0 <= prediction.confidence <= 1 for prediction in predictions)
    assert all(prediction.supportingEvidence for prediction in predictions)
    assert {prediction.kind for prediction in predictions} >= {
        "goal_completion_probability",
        "missed_deadline_risk",
        "emerging_blocker",
        "opportunity_forecast",
    }


def test_recommendations_are_ranked_by_expected_impact():
    recommendations = IntelligenceLoopService().snapshot().recommendations
    scores = [recommendation.rankedScore for recommendation in recommendations]

    assert scores == sorted(scores, reverse=True)
    assert all(recommendation.why for recommendation in recommendations)


def test_action_layer_requires_explicit_approval_and_never_executes_in_mock_mode():
    service = IntelligenceLoopService()
    action = service.snapshot().actionRequests[0]
    result = service.record_approval(ActionApprovalIn(actionRequestId=action.id, approved=True, note="Looks good"))

    assert action.permissionLevel == "explicit_user_approval"
    assert result["status"] == "approved"
    assert result["executed"] is False


def test_learn_records_outcome_with_future_adjustment():
    outcome = IntelligenceLoopService().record_outcome(
        LearningOutcomeIn(
            targetId="rec-wire-intelligence-loop",
            targetType="recommendation",
            outcome="successful",
            note="This became the platform foundation.",
        )
    )

    assert outcome.outcome == "successful"
    assert "Increase" in outcome.adjustment
