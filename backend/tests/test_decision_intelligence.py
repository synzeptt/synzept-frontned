from app.schemas.decision_intelligence import DecisionReviewUpdateIn
from app.services.decision_intelligence import DecisionIntelligenceService


def test_detection_only_suggests_high_confidence_decisions():
    candidates = DecisionIntelligenceService().detection_candidates(min_confidence=0.75)

    assert candidates
    assert all(candidate.confidence >= 0.75 for candidate in candidates)
    assert all(candidate.shouldSuggestDecision for candidate in candidates)
    assert all(candidate.evidence for candidate in candidates)


def test_decision_records_include_required_phase_one_fields():
    decision = DecisionIntelligenceService().decisions()[0]

    assert decision.title
    assert decision.description
    assert decision.importance
    assert decision.mission
    assert decision.goal
    assert decision.relatedProjects
    assert decision.alternativesConsidered
    assert decision.expectedOutcome
    assert decision.risks
    assert 0 <= decision.confidence <= 1
    assert decision.currentStatus


def test_decision_reviews_support_lifecycle_states_and_updates():
    service = DecisionIntelligenceService()
    reviews = service.reviews()
    result = service.update_review(
        DecisionReviewUpdateIn(
            decisionId=reviews[0].decisionId,
            reviewState="Completed",
            actualOutcome="Beta users understood the first screen quickly.",
            lessonsLearned=["Show explanations for ranked cards."],
        )
    )

    assert {review.reviewState for review in reviews} >= {"Pending", "Completed"}
    assert result["status"] == "updated"
    assert result["reviewState"] == "Completed"


def test_outcome_analysis_compares_expected_actual_and_lessons():
    outcome = DecisionIntelligenceService().outcome_analyses()[0]

    assert outcome.expectedOutcome
    assert outcome.actualOutcome
    assert outcome.predictionAccuracy >= 0
    assert outcome.lessonsLearned
    assert outcome.futureEvidence


def test_decision_dna_has_evidence_and_confidence():
    dna = DecisionIntelligenceService().decision_dna()

    assert dna
    assert all(trait.supportingEvidence for trait in dna)
    assert all(0 <= trait.confidence <= 1 for trait in dna)
    assert {trait.category for trait in dna} >= {"Common Strength", "High-Performing Pattern", "Blind Spot"}


def test_future_recommendations_reference_past_decisions_with_reasoning():
    recommendations = DecisionIntelligenceService().recommendations()

    assert recommendations
    assert all(recommendation.relevantDecisionIds for recommendation in recommendations)
    assert all(recommendation.reasoning for recommendation in recommendations)
    assert recommendations[0].expectedImpact >= recommendations[-1].expectedImpact
