from typing import Callable, Dict, Optional, Type
from threading import RLock

from .base import Connector
from .context import ConnectorContext
from .result import HealthResult
from .browser_connector import BrowserConnector


class ConnectorRegistry:
    def __init__(self):
        self._lock = RLock()
        self._registry: Dict[str, Type[Connector]] = {}

    def register_connector(self, capability: str, connector_cls: Type[Connector]) -> None:
        with self._lock:
            self._registry[capability.casefold()] = connector_cls

    def unregister_connector(self, capability: str) -> None:
        with self._lock:
            self._registry.pop(capability.casefold(), None)

    def get_connector_class(self, capability: str) -> Optional[Type[Connector]]:
        return self._registry.get(capability.casefold())

    def resolve(self, capability: str) -> Type[Connector]:
        connector = self.get_connector_class(capability)
        if connector is None:
            raise KeyError(f"Connector not found for capability: {capability}")
        return connector

    def health(self, capability: str, ctx: ConnectorContext) -> HealthResult:
        return self.resolve(capability)(config=ctx.config).health(ctx)

    def list_connectors(self) -> Dict[str, Type[Connector]]:
        return dict(self._registry)

    def autoregister(self, capability: str) -> Callable:
        def _decorator(cls: Type[Connector]):
            self.register_connector(capability, cls)
            return cls

        return _decorator


default_registry = ConnectorRegistry()

# Register the generic browser connector by default.
default_registry.register_connector("browser", BrowserConnector)
