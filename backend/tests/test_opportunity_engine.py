from app.services.opportunity_service import OpportunityEngineService


def test_opportunity_engine_returns_ranked_opportunities():
    service = OpportunityEngineService()
    opportunities = service.current_opportunities(limit=3)
    history = service.history_items()
    breakdown = service.score_breakdown(opportunities[0].id)

    assert len(opportunities) == 3
    assert opportunities[0].score >= opportunities[-1].score
    assert history
    assert breakdown is not None
    assert breakdown.totalScore >= breakdown.impactScore
