from app.services.life_graph_service import LifeGraphService


def test_life_graph_explore_returns_entities_and_relationships():
    service = LifeGraphService()
    result = service.explore(query="onboarding", entity_type="Task")

    assert result.entities
    assert result.relationships
    assert result.aiInsights
    assert result.paths == [] or result.paths
