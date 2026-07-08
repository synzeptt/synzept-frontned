# Decision Graph

The Decision Graph is Synzept's central decision knowledge structure. It represents decisions as first-class nodes connected to the context that influenced them and the outcomes, lessons, and future reasoning they produce.

## Graph Data Model

### Nodes

Nodes are typed entities:

- decision
- mission
- goal
- project
- people
- memory
- conversation
- evidence
- alternative
- risk
- outcome
- lesson

Decision nodes include unique ID, title, description, timestamp, confidence, status, and importance. Other nodes share the same envelope so future node types can be added without changing the graph renderer.

### Edges

Supported relationships:

- `influenced_by`
- `supports`
- `blocks`
- `resulted_in`
- `contradicts`
- `related_to`
- `reviewed_by`
- `learned_from`

Each edge includes source, target, relationship, label, strength, and evidence node IDs.

## Backend Architecture

- API router: `backend/app/api/decision_graph.py`
- Schemas: `backend/app/schemas/decision_graph.py`
- Service: `backend/app/services/decision_graph/service.py`
- Mock data: `backend/app/services/decision_graph/mock_data.py`
- Tests: `backend/tests/test_decision_graph.py`

## APIs

- `GET /api/internal/decision-graph`
  Returns the full graph. Optional `relationship` filter returns only matching edges and connected nodes.
- `GET /api/internal/decision-graph/nodes/decisions`
  Returns decision nodes only.
- `GET /api/internal/decision-graph/nodes/{node_id}`
  Returns the selected node's neighborhood, related insights, and chains.
- `GET /api/internal/decision-graph/insights`
  Returns graph-based insights ranked by impact and confidence.
- `GET /api/internal/decision-graph/chains`
  Returns cause-and-effect chains.

## Visualization

The interactive view lives at `/decisions/graph`. It supports:

- Exploring connected decisions.
- Filtering by relationship type.
- Selecting nodes to inspect context and evidence.
- Tracing cause-and-effect chains.
- Viewing graph insights with supporting connections.

The current graph uses stable positions for performance and predictability. A future version can swap the layout layer for a force-directed renderer without changing the graph API.

## Insight Rules

Insights must reference supporting graph connections. Phase 1 includes:

- Frequently repeated patterns.
- High-impact decisions.
- Common failure paths.
- Success clusters.
- Key turning points.

## Mock Boundary

This implementation uses realistic mock data only. It does not connect to production decisions, memories, conversations, projects, people, or outcomes. The graph service is modular so production retrieval, persistence, embeddings, and temporal graph expansion can be added behind the same contracts.
