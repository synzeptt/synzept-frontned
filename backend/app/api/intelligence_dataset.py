from fastapi import APIRouter

from app.schemas.intelligence_dataset import ConversationExtractIn, ExtractionResultOut, KnowledgeGraphOut, ReviewActionOut, ReviewEditIn, ReviewItemOut
from app.services.intelligence_dataset import IntelligenceDatasetService

router = APIRouter(prefix="/api/intelligence-dataset", tags=["intelligence-dataset"])


@router.get("/sample-conversation", response_model=dict)
async def sample_conversation():
    return IntelligenceDatasetService().sample_conversation()


@router.post("/extract", response_model=ExtractionResultOut)
async def extract_knowledge(body: ConversationExtractIn):
    return IntelligenceDatasetService().extract(body)


@router.get("/review", response_model=list[ReviewItemOut])
async def list_pending_review_items():
    return IntelligenceDatasetService().pending_review_items()


@router.post("/review/{review_item_id}/approve", response_model=ReviewActionOut)
async def approve_review_item(review_item_id: str, edits: ReviewEditIn | None = None):
    return IntelligenceDatasetService().approve(review_item_id, edits)


@router.post("/review/{review_item_id}/reject", response_model=ReviewActionOut)
async def reject_review_item(review_item_id: str):
    return IntelligenceDatasetService().reject(review_item_id)


@router.get("/graph", response_model=KnowledgeGraphOut)
async def graph_nodes():
    return IntelligenceDatasetService().graph()
