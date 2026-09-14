from typing import Callable, Dict, Optional, Type
from threading import RLock

from .base import Worker
from .browser_worker import BrowserWorker


class WorkerRegistry:
    """Registry for worker capability -> worker class mapping."""

    def __init__(self):
        self._lock = RLock()
        self._registry: Dict[str, Type[Worker]] = {}

    def register_worker(self, capability: str, worker_cls: Type[Worker]) -> None:
        with self._lock:
            self._registry[capability] = worker_cls

    def unregister_worker(self, capability: str) -> None:
        with self._lock:
            self._registry.pop(capability, None)

    def get_worker_class(self, capability: str) -> Optional[Type[Worker]]:
        return self._registry.get(capability)

    def list_workers(self) -> Dict[str, Type[Worker]]:
        return dict(self._registry)

    def autoregister(self, capability: str) -> Callable:
        def _decorator(cls: Type[Worker]):
            self.register_worker(capability, cls)
            return cls

        return _decorator


default_registry = WorkerRegistry()

# Register the generic browser worker by default.
default_registry.register_worker("browser", BrowserWorker)
