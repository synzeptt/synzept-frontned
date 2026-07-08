from app.services.evolution_engine import EvolutionEngineService


def test_evolution_engine_returns_expected_sections():
    service = EvolutionEngineService()

    insights = service.get_product_insights()
    recommendations = service.get_recommendations()
    adoption = service.get_feature_adoption()
    onboarding = service.get_onboarding_analysis()
    retention = service.get_retention_summary()
    dashboard = service.get_founder_dashboard()

    assert insights
    assert recommendations
    assert adoption["topFeatures"]
    assert onboarding["dropOffs"]
    assert retention["retentionRate"] >= 0
    assert dashboard["productHealth"]["score"] >= 0
    assert dashboard["topRecommendations"]
