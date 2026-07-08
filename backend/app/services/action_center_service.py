from __future__ import annotations

from app.schemas.action_center import ActionCenterOut
from app.services.action_center_mock_data import MOCK_ACTION_CENTER


class ActionCenterService:
    def __init__(self, data: dict | None = None) -> None:
        self.data = data or MOCK_ACTION_CENTER

    def get_dashboard(self) -> ActionCenterOut:
        return ActionCenterOut(**self.data)
