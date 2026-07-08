from app.services.pkm_service import PersonalKnowledgeModelService


def test_pkm_model_contains_expected_domains():
    model = PersonalKnowledgeModelService().get_model()

    assert model.userName
    assert model.summary
    assert len(model.domains) >= 6
    assert model.learningTimeline
