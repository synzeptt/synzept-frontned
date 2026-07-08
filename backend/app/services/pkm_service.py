from __future__ import annotations

from app.schemas.pkm import PkmModelOut
from app.services.pkm_mock_data import MOCK_PKM_MODEL


class PersonalKnowledgeModelService:
    def __init__(self, data: dict | None = None) -> None:
        self.data = data or MOCK_PKM_MODEL

    def get_model(self) -> PkmModelOut:
        return PkmModelOut(**self.data)
