from fastapi import APIRouter, Query

from app.schemas.skill_marketplace import SkillDeveloperManifestOut, SkillInstallActionOut, SkillMarketplaceItemOut
from app.services.skill_marketplace_service import SkillMarketplaceService

router = APIRouter(prefix="/api/internal/skill-marketplace")


@router.get("", response_model=list[SkillMarketplaceItemOut])
async def marketplace_home(query: str = Query(default="")):
    return SkillMarketplaceService().browse(query=query)


@router.get("/installed", response_model=list[SkillMarketplaceItemOut])
async def installed_skills():
    return SkillMarketplaceService().installed()


@router.get("/updates", response_model=list[SkillMarketplaceItemOut])
async def updates():
    return SkillMarketplaceService().updates()


@router.post("/install", response_model=SkillInstallActionOut)
async def install_skill(skill_id: str, action: str):
    return SkillMarketplaceService().install(skill_id, action)


@router.get("/developer-manifest/{skill_id}", response_model=SkillDeveloperManifestOut | None)
async def developer_manifest(skill_id: str):
    return SkillMarketplaceService().developer_manifest(skill_id)
