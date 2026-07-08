from fastapi import APIRouter

from app.schemas.pkm import PkmModelOut
from app.services.pkm_service import PersonalKnowledgeModelService

router = APIRouter(prefix="/api/internal/pkm")


@router.get("", response_model=PkmModelOut)
async def get_pkm_model():
    return PersonalKnowledgeModelService().get_model()
