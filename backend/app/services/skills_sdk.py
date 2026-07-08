from __future__ import annotations

from typing import Any, Protocol


class Skill(Protocol):
    name: str
    description: str
    category: str
    inputs: list[str]
    outputs: list[str]
    required_context: list[str]
    required_permissions: list[str]
    steps: list[str]
    completion_criteria: list[str]

    def metadata(self) -> dict[str, Any]:
        ...

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        ...


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def list(self) -> list[Skill]:
        return list(self._skills.values())

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)
