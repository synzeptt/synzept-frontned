from typing import Dict, Any


def generate_plan(goal: str, inputs: Dict[str, Any] = None) -> Dict[str, Any]:
    """Return a planner_output dict that the PlannerAdapter expects.

    For this validation sprint we map any greeting goal to the `mock-skill`.
    """
    inputs = inputs or {}
    return {
        "capability": "mock-skill",
        "goal": goal,
        "intent": "execute",
        "inputs": inputs,
    }
