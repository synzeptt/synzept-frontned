from typing import Callable, Dict, Optional, Type
from threading import RLock

from .base import Skill


class SkillRegistry:
    def __init__(self):
        self._lock = RLock()
        self._registry: Dict[str, Type[Skill]] = {}

    def register_skill(self, capability: str, skill_cls: Type[Skill]) -> None:
        with self._lock:
            self._registry[capability] = skill_cls

    def unregister_skill(self, capability: str) -> None:
        with self._lock:
            self._registry.pop(capability, None)

    def get_skill_class(self, capability: str) -> Optional[Type[Skill]]:
        return self._registry.get(capability)

    def list_skills(self) -> Dict[str, Type[Skill]]:
        return dict(self._registry)

    def autoregister(self, capability: str) -> Callable:
        def _decorator(cls: Type[Skill]):
            self.register_skill(capability, cls)
            return cls

        return _decorator


default_registry = SkillRegistry()

# Import built-ins once so planner resolution is data-driven and complete.
from . import research_skill  # noqa: E402,F401
from . import standard_skills  # noqa: E402,F401
