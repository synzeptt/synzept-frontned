from __future__ import annotations

from app.schemas.skill_marketplace import SkillDeveloperManifestOut, SkillInstallActionOut, SkillMarketplaceItemOut
from app.services.skill_marketplace_mock_data import MOCK_SKILL_CATALOG


class SkillMarketplaceService:
    def __init__(self, catalog: list[dict] | None = None) -> None:
        self.catalog = catalog or MOCK_SKILL_CATALOG

    def browse(self, query: str = "") -> list[SkillMarketplaceItemOut]:
        items = self.catalog
        if query:
            needle = query.lower()
            items = [item for item in items if needle in item["name"].lower() or needle in item["description"].lower()]
        return [SkillMarketplaceItemOut(**item) for item in items]

    def installed(self) -> list[SkillMarketplaceItemOut]:
        return [SkillMarketplaceItemOut(**item) for item in self.catalog if item.get("installed")]

    def updates(self) -> list[SkillMarketplaceItemOut]:
        return [SkillMarketplaceItemOut(**item) for item in self.catalog if item.get("version") and item.get("version") != "1.0.0"]

    def install(self, skill_id: str, action: str) -> SkillInstallActionOut:
        item = next((entry for entry in self.catalog if entry["id"] == skill_id), None)
        if not item:
            return SkillInstallActionOut(skillId=skill_id, action=action, status="error", message="Skill not found")
        if action == "install":
            item["installed"] = True
            item["enabled"] = True
            return SkillInstallActionOut(skillId=skill_id, action=action, status="ok", message="Skill installed and enabled")
        if action == "enable":
            item["enabled"] = True
            return SkillInstallActionOut(skillId=skill_id, action=action, status="ok", message="Skill enabled")
        if action == "disable":
            item["enabled"] = False
            return SkillInstallActionOut(skillId=skill_id, action=action, status="ok", message="Skill disabled")
        if action == "uninstall":
            item["installed"] = False
            item["enabled"] = False
            return SkillInstallActionOut(skillId=skill_id, action=action, status="ok", message="Skill removed")
        return SkillInstallActionOut(skillId=skill_id, action=action, status="ok", message="Action received")

    def developer_manifest(self, skill_id: str) -> SkillDeveloperManifestOut | None:
        item = next((entry for entry in self.catalog if entry["id"] == skill_id), None)
        if not item:
            return None
        return SkillDeveloperManifestOut(
            name=item["name"],
            version=item["version"],
            author=item["author"],
            category=item["category"],
            permissions=item["permissions"],
            integrations=item["integrations"],
            lifecycleHooks=["install", "enable", "disable", "update", "uninstall"],
        )
