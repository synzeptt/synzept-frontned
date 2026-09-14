# Connector Framework

Implements a generic connector layer that isolates external APIs behind a common contract.

Key files:
- `base.py` — Connector abstract contract
- `context.py` — `ConnectorContext` passed to every call
- `registry.py` — Automatic connector registration and discovery
- `manager.py` — Lifecycle, authentication, health, request orchestration
- `mock_connector.py` — Production-quality mock used in tests
- `runtime_integration.py` — Adapter for workers to call connectors

Events emitted: `connector.registered`, `connector.authenticate.*`, `connector.health.*`, `connector.request.*` (recorded in EventStore)
