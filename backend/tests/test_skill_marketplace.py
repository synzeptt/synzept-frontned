from app.services.skill_marketplace_service import SkillMarketplaceService


def test_marketplace_catalog_contains_featured_and_installed_skills():
    service = SkillMarketplaceService()
    catalog = service.browse()
    installed = service.installed()
    updates = service.updates()

    assert catalog
    assert any(item.featured for item in catalog)
    assert installed
    assert updates
