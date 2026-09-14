from typing import Dict, Any
from .manager import ConnectorManager
from .context import ConnectorContext
from app.events import default_event_bus


class ConnectorRuntimeAdapter:
    def __init__(self, manager: ConnectorManager = None, event_bus=None):
        self.manager = manager or ConnectorManager(event_bus=event_bus)
        self.events = event_bus or default_event_bus

    def perform(self, capability: str, method: str, ctx: ConnectorContext):
        # central entry point for workers to call connector methods
        self.events.emit("connector.request.initiated", {"capability": capability, "method": method, "execution_id": ctx.execution_id})
        res = self.manager.request(capability, method, ctx)
        return res
