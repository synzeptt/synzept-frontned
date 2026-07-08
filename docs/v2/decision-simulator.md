# Decision Simulator

The Decision Simulator helps users reason through important choices before committing. It does not claim certainty; it compares plausible futures using the user's context, Decision Graph connections, goals, missions, projects, memories, risk preference, and past outcomes.

## Architecture

- API router: `backend/app/api/decision_simulator.py`
- Schemas: `backend/app/schemas/decision_simulator.py`
- Service: `backend/app/services/decision_simulator/service.py`
- Mock data: `backend/app/services/decision_simulator/mock_data.py`
- UI route: `/decisions/simulator`
- UI component: `src/components/decision-simulator/DecisionSimulatorView.tsx`
- UI mock data: `src/lib/decision-simulator/`
- Tests: `backend/tests/test_decision_simulator.py`

## Inputs

Phase 1 mock simulations include:

- Personal knowledge signals.
- Decision Graph connections.
- Goals.
- Missions.
- Projects.
- Memories.
- Risk preference.
- Past outcome signals.

## Simulation Flow

1. Identify the decision.
2. Generate realistic options.
3. Estimate benefits and risks for each option.
4. Highlight assumptions.
5. Estimate confidence.
6. Present a comparison view.
7. Record the user's final choice in mock mode.
8. Revisit later to compare predicted versus actual outcomes.

## Scenario Model

Each scenario includes title, summary, potential benefits, potential risks, assumptions, confidence, best-case outcome, worst-case outcome, key uncertainties, and comparison metrics.

Comparison metrics:

- Effort
- Risk
- Cost
- Time
- Alignment with goals
- Expected impact

## APIs

- `GET /api/internal/decision-simulator`
  Returns available mock simulations.
- `GET /api/internal/decision-simulator/{simulation_id}`
  Returns one simulation.
- `GET /api/internal/decision-simulator/decision/{decision_id}`
  Returns the simulation for a decision.
- `POST /api/internal/decision-simulator/choice`
  Records the final choice in mock mode.
- `POST /api/internal/decision-simulator/outcome`
  Records an actual outcome and returns learning feedback.

## Learning

Once the real outcome is known, the simulator compares predicted and actual results, estimates accuracy, and stores lessons. These lessons should later become evidence for Decision DNA and future simulations.

## Production Boundary

This implementation uses realistic mock data only. It does not connect to production knowledge, decisions, graph data, memories, projects, or user preferences. The contracts are shaped for future expansion behind the same API.
