from fastapi import APIRouter

from app.schemas.privacy_intelligence import (
    GlobalPatternOut,
    PrivacyContributionSettingsIn,
    PrivacyContributionSettingsOut,
    PrivacyIntelligenceOut,
    PrivacyRecommendationOut,
)
from app.services.privacy_intelligence import PrivacyIntelligenceService

router = APIRouter(prefix="/api/internal/privacy-intelligence")


@router.get("", response_model=PrivacyIntelligenceOut)
async def privacy_intelligence_snapshot():
    return PrivacyIntelligenceService().snapshot()


@router.get("/recommendations", response_model=list[PrivacyRecommendationOut])
async def privacy_recommendations():
    return PrivacyIntelligenceService().recommendations()


@router.get("/global-patterns", response_model=list[GlobalPatternOut])
async def global_patterns():
    return PrivacyIntelligenceService().global_patterns()


@router.get("/contribution-settings", response_model=PrivacyContributionSettingsOut)
async def contribution_settings():
    return PrivacyIntelligenceService().contribution_settings()


@router.post("/contribution-settings", response_model=PrivacyContributionSettingsOut)
async def update_contribution_settings(body: PrivacyContributionSettingsIn):
    return PrivacyIntelligenceService().update_contribution_settings(body)
