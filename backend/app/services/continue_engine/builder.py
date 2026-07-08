from app.schemas.continue_context import ContinueContextOut
from app.services.continue_context_service import ContinueContextService


class ContinueContextBuilder:
    def __init__(self, session) -> None:
        self.session = session

    async def build(self, user) -> ContinueContextOut:
        # Reuse the existing ContinueContextService which already builds detailed cards and context
        return await ContinueContextService(self.session).get_context(user)
