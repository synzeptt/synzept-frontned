from app.services.open_loops_engine_service import OpenLoopsEngineService


class OpenLoopDetector:
    def __init__(self, session) -> None:
        self.session = session

    async def detect(self, user):
        engine = await OpenLoopsEngineService(self.session).list(user.id)
        # return top open loops as simple dicts
        return [
            {"id": item.id, "title": item.title, "description": getattr(item, "description", "")}
            for item in engine.items[:8]
        ]
