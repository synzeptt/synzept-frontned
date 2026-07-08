from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.schemas.decision_simulator import (
    DecisionSimulationOut,
    FinalChoiceIn,
    SimulationOutcomeIn,
    SimulationLearningOut,
)
from app.services.decision_simulator.mock_data import MOCK_DECISION_SIMULATIONS


class DecisionSimulatorService:
    def __init__(self, simulations: list[dict[str, Any]] | None = None) -> None:
        self.simulations = deepcopy(simulations or MOCK_DECISION_SIMULATIONS)

    def list_simulations(self) -> list[DecisionSimulationOut]:
        return [DecisionSimulationOut(**simulation) for simulation in self.simulations]

    def get_simulation(self, simulation_id: str) -> DecisionSimulationOut | None:
        match = next((simulation for simulation in self.simulations if simulation["id"] == simulation_id), None)
        return DecisionSimulationOut(**match) if match else None

    def simulation_for_decision(self, decision_id: str) -> DecisionSimulationOut | None:
        match = next((simulation for simulation in self.simulations if simulation["inputContext"]["decisionId"] == decision_id), None)
        return DecisionSimulationOut(**match) if match else None

    def record_choice(self, body: FinalChoiceIn) -> dict[str, str | bool]:
        simulation = next((item for item in self.simulations if item["id"] == body.simulationId), None)
        if not simulation:
            return {"status": "not_found", "simulationId": body.simulationId, "recorded": False}
        scenario_ids = {scenario["id"] for scenario in simulation["scenarios"]}
        if body.scenarioId not in scenario_ids:
            return {"status": "scenario_not_found", "simulationId": body.simulationId, "recorded": False}
        simulation["finalChoice"] = {
            "scenarioId": body.scenarioId,
            "chosenAt": "2026-07-07T18:35:00+05:30",
            "rationale": body.rationale,
            "status": "recorded_mock",
        }
        return {"status": "recorded_mock", "simulationId": body.simulationId, "scenarioId": body.scenarioId, "recorded": True}

    def record_outcome(self, body: SimulationOutcomeIn) -> SimulationLearningOut | None:
        simulation = next((item for item in self.simulations if item["id"] == body.simulationId), None)
        if not simulation:
            return None
        scenario = next((item for item in simulation["scenarios"] if item["id"] == body.scenarioId), None)
        if not scenario:
            return None
        learning = SimulationLearningOut(
            id=f"learn-{body.simulationId}",
            scenarioId=body.scenarioId,
            predictedResult=scenario["bestCaseOutcome"],
            actualResult=body.actualResult,
            accuracy=76,
            lessonsLearned=body.lessonsLearned,
        )
        simulation["learning"] = learning.model_dump()
        return learning
