from typing import Any, Callable, Dict, List
import logging


class EventStore:
    def __init__(self):
        self._events: List[Dict[str, Any]] = []

    def record(self, event: Dict[str, Any]) -> None:
        self._events.append(event)

    def list(self) -> List[Dict[str, Any]]:
        return list(self._events)


class EventBus:
    def __init__(self, store: EventStore = None):
        self._subs: Dict[str, List[Callable]] = {}
        self.store = store or EventStore()

    def subscribe(self, event_type: str, fn: Callable) -> None:
        self._subs.setdefault(event_type, []).append(fn)

    def emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        event = {"type": event_type, "payload": payload}
        # persist first
        try:
            self.store.record(event)
        except Exception:
            logging.exception("failed to persist event")
        # notify subscribers
        for fn in self._subs.get(event_type, []):
            try:
                fn(event)
            except Exception:
                logging.exception("event handler failed")


default_event_bus = EventBus()
