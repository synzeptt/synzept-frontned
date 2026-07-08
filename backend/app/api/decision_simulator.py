from fastapi import APIRouter

from app.schemas.decision_simulator import DecisionSimulationOut, FinalChoiceIn, SimulationLearningOut, SimulationOutcomeIn
from app.services.decision_simulator import DecisionSimulatorService

router = APIRouter(prefix="/api/internal/decision-simulator")


@router.get("", response_model=list[DecisionSimulationOut])
async def simulations():
    return DecisionSimulatorService().list_simulations()


@router.get("/{simulation_id}", response_model=DecisionSimulationOut | None)
async def simulation_detail(simulation_id: str):
    return DecisionSimulatorService().get_simulation(simulation_id)


@router.get("/decision/{decision_id}", response_model=DecisionSimulationOut | None)
async def simulation_for_decision(decision_id: str):
    return DecisionSimulatorService().simulation_for_decision(decision_id)


@router.post("/choice", response_model=dict)
async def record_final_choice(body: FinalChoiceIn):
    return DecisionSimulatorService().record_choice(body)


@router.post("/outcome", response_model=SimulationLearningOut | None)
async def record_simulation_outcome(body: SimulationOutcomeIn):
    return DecisionSimulatorService().record_outcome(body)
