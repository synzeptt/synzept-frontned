from __future__ import annotations

from typing import Any

from app.services.skills_sdk import SkillRegistry
from app.services.skills_mock_data import MOCK_SKILLS


class MockSkillRegistry(SkillRegistry):
    def __init__(self) -> None:
        super().__init__()
        for skill_data in MOCK_SKILLS:
            self.register(_MockSkill(skill_data))


class _MockSkill:
    def __init__(self, data: dict[str, Any]) -> None:
        self.name = data["name"]
        self.description = data["description"]
        self.category = data["category"]
        self.inputs = data["inputs"]
        self.outputs = data["outputs"]
        self.required_context = data["requiredContext"]
        self.required_permissions = data["requiredPermissions"]
        self.steps = data["steps"]
        self.completion_criteria = data["completionCriteria"]
        self._data = data

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "requiredContext": self.required_context,
            "requiredPermissions": self.required_permissions,
            "steps": self.steps,
            "completionCriteria": self.completion_criteria,
        }

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "skillName": self.name,
            "status": "ready",
            "plan": self.steps,
            "result": f"Mock execution for {self.name} using {context.get('goal', 'current context')}",
        }
