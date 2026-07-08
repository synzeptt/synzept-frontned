from fastapi import APIRouter

from app.services.evolution_engine import EvolutionEngineService

router = APIRouter(prefix="/api/internal/evolution")


@router.get("/insights")
async def get_product_insights():
    return {"insights": EvolutionEngineService().get_product_insights()}


@router.get("/recommendations")
async def get_recommendations():
    return {"recommendations": EvolutionEngineService().get_recommendations()}


@router.get("/feature-adoption")
async def get_feature_adoption():
    return EvolutionEngineService().get_feature_adoption()


@router.get("/onboarding-analysis")
async def get_onboarding_analysis():
    return EvolutionEngineService().get_onboarding_analysis()


@router.get("/retention-summary")
async def get_retention_summary():
    return EvolutionEngineService().get_retention_summary()


@router.get("/founder-dashboard")
async def get_founder_dashboard():
    return EvolutionEngineService().get_founder_dashboard()
