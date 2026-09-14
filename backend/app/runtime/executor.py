from __future__ import annotations

from typing import Protocol

from .types import ExecutionContext, ExecutionStep


class StepExecutor(Protocol):
    name: str

    async def execute(self, *, step: ExecutionStep, context: ExecutionContext) -> dict:
        ...
