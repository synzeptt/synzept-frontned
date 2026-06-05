import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.dependencies import get_current_user, get_db
from app.core.exceptions import NotFoundError
from app.database.base import Base
from app.main import app
from app.models.user import User
from app.schemas.relationship_graph_phase5 import RelationshipEdgeCreate, RelationshipNodeCreate
from app.services.relationship_graph_phase5_service import RelationshipGraphPhase5Service


@pytest.fixture
def client(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'relationship-graph.db'}")

    async def create_schema():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    user = User(id=uuid4(), email="relationship-graph@example.com", is_active=True)

    async def override_user():
        return user

    async def override_db():
        async with session_factory() as session:
            session.add(user)
            await session.flush()
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_relationship_graph_api_lifecycle_and_neighborhood(client):
    project = client.post(
        "/api/relationship-graph/nodes",
        json={"nodeType": "project", "title": "Synzept V2", "description": "Continuity operating system"},
    )
    assert project.status_code == 200

    decision = client.post(
        "/api/relationship-graph/nodes",
        json={"nodeType": "decision", "title": "Use explicit approval", "description": "Trust matters"},
    )
    assert decision.status_code == 200

    edge = client.post(
        "/api/relationship-graph/edges",
        json={
            "sourceNodeId": decision.json()["id"],
            "targetNodeId": project.json()["id"],
            "relationshipType": "guides",
            "reason": "The trust rule shapes Project Intelligence and Learning Engine behavior.",
            "strength": 0.9,
        },
    )
    assert edge.status_code == 200
    assert edge.json()["reason"].startswith("The trust rule")

    graph = client.get("/api/relationship-graph")
    assert graph.status_code == 200
    assert len(graph.json()["nodes"]) == 2
    assert len(graph.json()["edges"]) == 1

    neighborhood = client.get(f"/api/relationship-graph/nodes/{project.json()['id']}")
    assert neighborhood.status_code == 200
    assert neighborhood.json()["node"]["title"] == "Synzept V2"
    assert neighborhood.json()["relatedNodes"][0]["title"] == "Use explicit approval"

    updated = client.put(
        f"/api/relationship-graph/edges/{edge.json()['id']}",
        json={"relationshipType": "explains", "strength": 0.8},
    )
    assert updated.status_code == 200
    assert updated.json()["relationshipType"] == "explains"

    assert client.delete(f"/api/relationship-graph/edges/{edge.json()['id']}").status_code == 200
    assert client.delete(f"/api/relationship-graph/nodes/{decision.json()['id']}").status_code == 200


@pytest.mark.asyncio
async def test_relationship_graph_rejects_cross_user_edges(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'relationship-cross-user.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    owner_id = uuid4()
    other_id = uuid4()
    async with session_factory() as session:
        session.add_all([User(id=owner_id, email="owner-graph@example.com"), User(id=other_id, email="other-graph@example.com")])
        await session.flush()
        service = RelationshipGraphPhase5Service(session)
        source = await service.create_node(owner_id, RelationshipNodeCreate(nodeType="user", title="Owner"))
        target = await service.create_node(other_id, RelationshipNodeCreate(nodeType="project", title="Other project"))

        with pytest.raises(NotFoundError):
            await service.create_edge(
                owner_id,
                RelationshipEdgeCreate(
                    sourceNodeId=source["id"],
                    targetNodeId=target["id"],
                    relationshipType="should_not_link",
                ),
            )

    await engine.dispose()
