from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.core import (
    CoreGoalCreate, CoreGoalOut, CoreGoalUpdate,
    CoreMemoryCreate, CoreMemoryOut, CoreMemoryUpdate,
    CoreProjectCreate, CoreProjectOut, CoreProjectUpdate,
    GraphEdgeCreate, GraphEdgeOut, GraphEdgeUpdate,
    GraphNodeCreate, GraphNodeOut, GraphNodeUpdate,
    LearningSignalCreate, LearningSignalOut, LearningSignalUpdate,
    TimelineEventCreate, TimelineEventOut, TimelineEventUpdate,
)
from app.services.goal_service import GoalService
from app.services.graph_service import GraphService
from app.services.learning_service import LearningService
from app.services.memory_service import CoreMemoryService
from app.services.project_service import ProjectService
from app.services.timeline_service import TimelineService

router = APIRouter(prefix="/core")


@router.get("/projects", response_model=list[CoreProjectOut])
async def list_projects(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ProjectService(session).list(user.id)


@router.post("/projects", response_model=CoreProjectOut)
async def create_project(body: CoreProjectCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ProjectService(session).create(user.id, body)


@router.get("/projects/{item_id}", response_model=CoreProjectOut)
async def get_project(item_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ProjectService(session).get(user.id, item_id)


@router.patch("/projects/{item_id}", response_model=CoreProjectOut)
async def update_project(item_id: UUID, body: CoreProjectUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ProjectService(session).update(user.id, item_id, body)


@router.delete("/projects/{item_id}")
async def delete_project(item_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    await ProjectService(session).delete(user.id, item_id)
    return {"ok": True}


@router.get("/goals", response_model=list[CoreGoalOut])
async def list_goals(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GoalService(session).list(user.id)


@router.post("/goals", response_model=CoreGoalOut)
async def create_goal(body: CoreGoalCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GoalService(session).create(user.id, body)


@router.get("/goals/{item_id}", response_model=CoreGoalOut)
async def get_goal(item_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GoalService(session).get(user.id, item_id)


@router.patch("/goals/{item_id}", response_model=CoreGoalOut)
async def update_goal(item_id: UUID, body: CoreGoalUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GoalService(session).update(user.id, item_id, body)


@router.delete("/goals/{item_id}")
async def delete_goal(item_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    await GoalService(session).delete(user.id, item_id)
    return {"ok": True}


@router.get("/memories", response_model=list[CoreMemoryOut])
async def list_memories(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await CoreMemoryService(session).list(user.id)


@router.post("/memories", response_model=CoreMemoryOut)
async def create_memory(body: CoreMemoryCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await CoreMemoryService(session).create(user.id, body)


@router.get("/memories/{item_id}", response_model=CoreMemoryOut)
async def get_memory(item_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await CoreMemoryService(session).get(user.id, item_id)


@router.patch("/memories/{item_id}", response_model=CoreMemoryOut)
async def update_memory(item_id: UUID, body: CoreMemoryUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await CoreMemoryService(session).update(user.id, item_id, body)


@router.delete("/memories/{item_id}")
async def delete_memory(item_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    await CoreMemoryService(session).delete(user.id, item_id)
    return {"ok": True}


@router.get("/timeline-events", response_model=list[TimelineEventOut])
async def list_timeline_events(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await TimelineService(session).list(user.id)


@router.post("/timeline-events", response_model=TimelineEventOut)
async def create_timeline_event(body: TimelineEventCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await TimelineService(session).create(user.id, body)


@router.get("/timeline-events/{item_id}", response_model=TimelineEventOut)
async def get_timeline_event(item_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await TimelineService(session).get(user.id, item_id)


@router.patch("/timeline-events/{item_id}", response_model=TimelineEventOut)
async def update_timeline_event(item_id: UUID, body: TimelineEventUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await TimelineService(session).update(user.id, item_id, body)


@router.delete("/timeline-events/{item_id}")
async def delete_timeline_event(item_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    await TimelineService(session).delete(user.id, item_id)
    return {"ok": True}


@router.get("/learning-signals", response_model=list[LearningSignalOut])
async def list_learning_signals(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await LearningService(session).list(user.id)


@router.post("/learning-signals", response_model=LearningSignalOut)
async def create_learning_signal(body: LearningSignalCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await LearningService(session).create(user.id, body)


@router.get("/learning-signals/{item_id}", response_model=LearningSignalOut)
async def get_learning_signal(item_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await LearningService(session).get(user.id, item_id)


@router.patch("/learning-signals/{item_id}", response_model=LearningSignalOut)
async def update_learning_signal(item_id: UUID, body: LearningSignalUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await LearningService(session).update(user.id, item_id, body)


@router.delete("/learning-signals/{item_id}")
async def delete_learning_signal(item_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    await LearningService(session).delete(user.id, item_id)
    return {"ok": True}


@router.get("/graph/nodes", response_model=list[GraphNodeOut])
async def list_graph_nodes(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GraphService(session).list_nodes(user.id)


@router.post("/graph/nodes", response_model=GraphNodeOut)
async def create_graph_node(body: GraphNodeCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GraphService(session).create_node(user.id, body)


@router.get("/graph/nodes/{item_id}", response_model=GraphNodeOut)
async def get_graph_node(item_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GraphService(session).get_node(user.id, item_id)


@router.patch("/graph/nodes/{item_id}", response_model=GraphNodeOut)
async def update_graph_node(item_id: UUID, body: GraphNodeUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GraphService(session).update_node(user.id, item_id, body)


@router.delete("/graph/nodes/{item_id}")
async def delete_graph_node(item_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    await GraphService(session).delete_node(user.id, item_id)
    return {"ok": True}


@router.get("/graph/edges", response_model=list[GraphEdgeOut])
async def list_graph_edges(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GraphService(session).list_edges(user.id)


@router.post("/graph/edges", response_model=GraphEdgeOut)
async def create_graph_edge(body: GraphEdgeCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GraphService(session).create_edge(user.id, body)


@router.get("/graph/edges/{item_id}", response_model=GraphEdgeOut)
async def get_graph_edge(item_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GraphService(session).get_edge(user.id, item_id)


@router.patch("/graph/edges/{item_id}", response_model=GraphEdgeOut)
async def update_graph_edge(item_id: UUID, body: GraphEdgeUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GraphService(session).update_edge(user.id, item_id, body)


@router.delete("/graph/edges/{item_id}")
async def delete_graph_edge(item_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    await GraphService(session).delete_edge(user.id, item_id)
    return {"ok": True}
