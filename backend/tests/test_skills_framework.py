from app.services.skill_registry import MockSkillRegistry


def test_skill_registry_exposes_mock_skills():
    registry = MockSkillRegistry()
    skills = registry.list()

    assert len(skills) >= 10
    assert any(skill.name == "Launch Planner" for skill in skills)
    assert any(skill.name == "Daily Planning" for skill in skills)
