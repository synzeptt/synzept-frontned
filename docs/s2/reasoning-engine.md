# Sprint 2 Reasoning Engine

The Reasoning Engine is the reasoning-first layer that plans a response before any LLM is called. The LLM receives structured context, a reasoning plan, supporting evidence, and guardrails. It generates language; it does not make product decisions.

## Architecture

Base package: `backend/app/services/reasoning_engine`

- `components.py`: independent pipeline modules.
- `service.py`: pipeline orchestration.
- `mock_data.py`: mock context, memories, knowledge, and decisions.
- `schemas/reasoning_engine.py`: API contracts and LLM handoff model.
- `api/reasoning_engine.py`: mock REST endpoints.

## Pipeline

1. Intent Analysis
2. Context Retrieval
3. Memory Retrieval
4. Knowledge Graph Lookup
5. Decision History Lookup
6. Evidence Collection
7. Risk Analysis
8. Opportunity Analysis
9. Planning
10. Response Generation

## Component Interfaces

Each module implements:

```python
class ReasoningComponent:
    name: str
    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        ...
```

This keeps modules independently testable and lets future modules be inserted without changing existing component internals.

## Planner Contract

The planner determines:

- whether enough information exists
- whether clarification is needed
- relevant memories
- similar decisions
- evidence to include
- risks and opportunities to mention
- recommendation
- response strategy
- LLM instructions

The output is a structured `ReasoningPlanOut`.

## LLM Layer

The LLM handoff contains:

- `role`: `language_generation_only`
- `structuredContext`
- `reasoningPlan`
- `supportingEvidence`
- `guardrails`

The response composer currently creates a mock language response, but the contract is ready for a real LLM composer later.

## APIs

Base path: `/api/reasoning-engine`

- `GET /examples`: mock reasoning requests.
- `POST /reason`: run the full reasoning pipeline and return the response plan plus LLM handoff.

## UI

The workspace screen is available at `/reasoning-engine`.

It shows:

- all pipeline stages
- evidence and risks
- planner output
- LLM handoff guardrails
- opportunity analysis

## Tests

Tests cover:

- required pipeline order
- structured planner output
- clarification path
- LLM handoff guardrails and evidence

This sprint uses mock data only and does not call an LLM or production data sources.
