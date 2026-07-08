# Synzept V2 Agent Runtime

## Overview

The Agent Runtime is a mock-driven long-running agent system for managing persistent goals, planning next steps, executing approved workflows, and monitoring progress.

## Backend architecture

- Runtime: app/agents/runtime.py
- Models: app/agents/models.py
- Planner: app/agents/planner.py
- Executor: app/agents/executor.py
- Monitor: app/agents/monitor.py
- Approval manager: app/agents/approval_manager.py
- Progress tracker: app/agents/progress_tracker.py
- Agent memory: app/agents/agent_memory.py
- Mock data: app/agents/mock_data.py

## API routes

- GET /api/internal/agent-runtime
- GET /api/internal/agent-runtime/{agent_id}
- POST /api/internal/agent-runtime/{agent_id}/plan
- POST /api/internal/agent-runtime/{agent_id}/execute
- POST /api/internal/agent-runtime/{agent_id}/monitor
- POST /api/internal/agent-runtime/{agent_id}/progress
- POST /api/internal/agent-runtime/{agent_id}/remember

## UI

- Dashboard with active agents, objective, current step, confidence, health, last activity, and upcoming actions.

## Tests

- Backend tests validate that agents can be listed and planned.
