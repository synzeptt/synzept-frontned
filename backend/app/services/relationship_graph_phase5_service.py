from collections import Counter
from datetime import datetime, timezone
import re
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.conversation import Conversation
from app.models.goal import Goal
from app.models.memory import Memory
from app.models.note import Note
from app.models.project import Project
from app.models.project_intelligence import ProjectDecision, ProjectOpenLoop
from app.models.project_intelligence_phase2 import Decision, OpenLoop
from app.models.relationship_graph_phase5 import RelationshipEdge, RelationshipNode
from app.models.task import Task
from app.models.timeline_event import TimelineEvent
from app.schemas.relationship_graph_phase5 import (
    GraphAnswerOut,
    GraphContextItemOut,
    GraphContextOut,
    RelationshipEdgeCreate,
    RelationshipEdgeUpdate,
    RelationshipNodeCreate,
    RelationshipNodeUpdate,
)


class RelationshipGraphPhase5Service:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def graph(self, user_id: UUID) -> dict:
        return {"nodes": [self._node_out(item) for item in await self.list_nodes(user_id)], "edges": [self._edge_out(item) for item in await self.list_edges(user_id)]}

    async def refresh(self, user_id: UUID) -> dict:
        node_cache: dict[tuple[str, str], RelationshipNode] = {}

        def entity_key(node_type: str, entity_id, title: str = "") -> tuple[str, str]:
            if entity_id:
                return (node_type, str(entity_id))
            if node_type == "user":
                return (node_type, "self")
            return (node_type, title.strip().casefold())

        async def node(node_type: str, entity_id, title: str, description: str = "") -> RelationshipNode:
            key = entity_key(node_type, entity_id, title)
            clauses = [
                RelationshipNode.user_id == user_id,
                RelationshipNode.node_type == node_type,
            ]
            if entity_id:
                clauses.append(RelationshipNode.entity_id == entity_id)
            elif node_type == "user":
                clauses.append(RelationshipNode.entity_id.is_(None))
            else:
                clauses.extend((RelationshipNode.entity_id.is_(None), RelationshipNode.title == title[:240]))
            if key in node_cache:
                return node_cache[key]
            result = await self.session.execute(
                select(RelationshipNode).where(*clauses)
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.title = title[:240]
                existing.description = description or ""
                existing.updated_at = datetime.now(timezone.utc)
                node_cache[key] = existing
                return existing
            created = RelationshipNode(
                user_id=user_id,
                node_type=node_type,
                entity_id=entity_id,
                title=title[:240],
                description=description or "",
            )
            self.session.add(created)
            await self.session.flush()
            node_cache[key] = created
            return created

        async def edge(source: RelationshipNode, target: RelationshipNode, relationship_type: str, reason: str, strength: float = 0.7) -> None:
            if source.id == target.id:
                return
            result = await self.session.execute(
                select(RelationshipEdge).where(
                    RelationshipEdge.user_id == user_id,
                    RelationshipEdge.source_node_id == source.id,
                    RelationshipEdge.target_node_id == target.id,
                    RelationshipEdge.relationship_type == relationship_type,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.reason = reason
                existing.strength = strength
                existing.updated_at = datetime.now(timezone.utc)
                return
            self.session.add(
                RelationshipEdge(
                    user_id=user_id,
                    source_node_id=source.id,
                    target_node_id=target.id,
                    relationship_type=relationship_type,
                    reason=reason,
                    strength=strength,
                )
            )

        projects = await self._projects(user_id)
        goals = await self._goals(user_id)
        tasks = await self._tasks(user_id)
        notes = await self._notes(user_id)
        memories = await self._memories(user_id)
        conversations = await self._conversations(user_id)
        decisions = await self._decisions(user_id)
        legacy_decisions = await self._legacy_decisions(user_id)
        loops = await self._open_loops(user_id)
        legacy_loops = await self._legacy_open_loops(user_id)
        timeline = await self._timeline(user_id)

        user_node = await node("user", None, "You", "Workspace owner")
        project_lookup = {item.id: item for item in projects}
        project_nodes = {item.id: await node("project", item.id, item.name, item.context_summary or item.description or "") for item in projects}
        goal_nodes = {item.id: await node("goal", item.id, item.title, item.description or "") for item in goals}

        for project_node in project_nodes.values():
            await edge(user_node, project_node, "supports", "This project belongs to your workspace.", 0.85)
        for goal in goals:
            goal_node = goal_nodes[goal.id]
            await edge(user_node, goal_node, "supports", "This goal belongs to your workspace.", 0.82)
            if goal.project_id and goal.project_id in project_nodes:
                await edge(project_nodes[goal.project_id], goal_node, "supports", f"{project_lookup[goal.project_id].name} supports {goal.title}.", 0.86)
        for task in tasks:
            task_node = await node("task", task.id, task.title, task.description or f"Status: {task.status}")
            await edge(user_node, task_node, "related_to", "This task belongs to your workspace.", 0.62)
            if task.project_id and task.project_id in project_nodes:
                await edge(task_node, project_nodes[task.project_id], "supports", f"{task.title} moves this project forward.", 0.84)
            if getattr(task, "milestone_id", None):
                await edge(task_node, user_node, "depends_on", "This task depends on its milestone sequence.", 0.55)
        for note in notes:
            note_node = await node("note", note.id, note.title or "Untitled note", note.summary or note.content[:240])
            knowledge_node = await node("knowledge", note.id, note.title or "Knowledge note", note.summary or note.content[:240])
            await edge(note_node, knowledge_node, "created_from", "This knowledge was created from a note.", 0.72)
            if note.project_id and note.project_id in project_nodes:
                await edge(knowledge_node, project_nodes[note.project_id], "supports", "This knowledge preserves project context.", 0.72)
            if note.goal_id and note.goal_id in goal_nodes:
                await edge(knowledge_node, goal_nodes[note.goal_id], "supports", "This knowledge preserves goal context.", 0.72)
        for memory in memories:
            memory_node = await node("memory", memory.id, memory.summary or memory.content[:80], memory.content[:240])
            knowledge_node = await node("knowledge", memory.id, memory.summary or memory.content[:80], memory.content[:240])
            await edge(memory_node, knowledge_node, "created_from", "This knowledge was created from memory.", 0.78)
            await edge(user_node, knowledge_node, "related_to", "This knowledge is part of your approved workspace context.", min(max(memory.importance_score, 0.45), 0.95))
            if memory.project_id and memory.project_id in project_nodes:
                await edge(knowledge_node, project_nodes[memory.project_id], "supports", "This knowledge is tied to project context.", 0.76)
        for conversation in conversations:
            conversation_node = await node("conversation", conversation.id, conversation.title or "Untitled conversation", conversation.summary or conversation.active_intent or "")
            if conversation.project_id and conversation.project_id in project_nodes:
                await edge(conversation_node, project_nodes[conversation.project_id], "created_from", "This conversation created project context.", 0.72)
        for decision in decisions:
            detail = decision.description or decision.reason or decision.outcome or f"Status: {decision.status}"
            decision_node = await node("decision", decision.id, decision.title, detail)
            if decision.project_id in project_nodes:
                await edge(decision_node, project_nodes[decision.project_id], "influences", "This decision shapes project direction.", 0.88)
        for decision in legacy_decisions:
            decision_node = await node("decision", decision.id, decision.decision, f"Status: {decision.status}")
            if decision.project_id in project_nodes:
                await edge(decision_node, project_nodes[decision.project_id], "influences", "This decision shapes project direction.", 0.84)
        for loop_item in loops:
            loop_node = await node("open_loop", loop_item.id, loop_item.title, loop_item.description or f"Status: {loop_item.status}")
            if loop_item.project_id in project_nodes:
                await edge(loop_node, project_nodes[loop_item.project_id], "blocks", "This unfinished work can block project momentum.", 0.9)
        for loop_item in legacy_loops:
            loop_node = await node("open_loop", loop_item.id, loop_item.loop, f"Status: {loop_item.status}")
            if loop_item.project_id in project_nodes:
                await edge(loop_node, project_nodes[loop_item.project_id], "blocks", "This unfinished work can block project momentum.", 0.86)
        for event in timeline:
            event_node = await node("timeline_event", event.id, event.title, event.description or event.event_type)
            await edge(event_node, user_node, "created_from", "This event is part of your workspace history.", 0.55 + min(event.importance, 0.4))
            if event.project_id and event.project_id in project_nodes:
                await edge(event_node, project_nodes[event.project_id], "influences", "This event changed project context.", 0.72 + min(event.importance, 0.2))

        await self._person_edges(user_id, node, edge, [*notes, *memories, *conversations], project_nodes)

        await self._keyword_edges(user_id)
        await self.session.flush()
        return await self.graph(user_id)

    async def list_nodes(self, user_id: UUID) -> list[RelationshipNode]:
        result = await self.session.execute(
            select(RelationshipNode).where(RelationshipNode.user_id == user_id).order_by(RelationshipNode.created_at.desc())
        )
        return list(result.scalars())

    async def get_node(self, user_id: UUID, node_id: UUID) -> RelationshipNode:
        result = await self.session.execute(
            select(RelationshipNode).where(RelationshipNode.id == node_id, RelationshipNode.user_id == user_id)
        )
        node = result.scalar_one_or_none()
        if not node:
            raise NotFoundError("Relationship node not found")
        return node

    async def node_for_entity(self, user_id: UUID, node_type: str, entity_id: UUID) -> dict:
        result = await self.session.execute(
            select(RelationshipNode).where(
                RelationshipNode.user_id == user_id,
                RelationshipNode.node_type == node_type,
                RelationshipNode.entity_id == entity_id,
            )
        )
        node = result.scalar_one_or_none()
        if not node:
            raise NotFoundError("Relationship node not found")
        return await self.neighborhood(user_id, node.id)

    async def create_node(self, user_id: UUID, data: RelationshipNodeCreate) -> dict:
        node = RelationshipNode(
            user_id=user_id,
            node_type=data.nodeType,
            entity_id=data.entityId,
            title=data.title.strip(),
            description=data.description.strip(),
        )
        self.session.add(node)
        await self.session.flush()
        return self._node_out(node)

    async def update_node(self, user_id: UUID, node_id: UUID, data: RelationshipNodeUpdate) -> dict:
        node = await self.get_node(user_id, node_id)
        if data.title is not None:
            node.title = data.title.strip()
        if data.description is not None:
            node.description = data.description.strip()
        node.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return self._node_out(node)

    async def delete_node(self, user_id: UUID, node_id: UUID) -> None:
        await self.session.delete(await self.get_node(user_id, node_id))

    async def list_edges(self, user_id: UUID) -> list[RelationshipEdge]:
        result = await self.session.execute(
            select(RelationshipEdge).where(RelationshipEdge.user_id == user_id).order_by(RelationshipEdge.created_at.desc())
        )
        return list(result.scalars())

    async def insights(self, user_id: UUID) -> list[dict]:
        graph = await self.graph(user_id)
        nodes = graph["nodes"]
        edges = graph["edges"]
        degree: dict[str, int] = {str(node["id"]): 0 for node in nodes}
        for edge in edges:
            degree[str(edge["sourceNodeId"])] = degree.get(str(edge["sourceNodeId"]), 0) + 1
            degree[str(edge["targetNodeId"])] = degree.get(str(edge["targetNodeId"]), 0) + 1
        node_by_id = {str(node["id"]): node for node in nodes}
        isolated = [node for node in nodes if degree.get(str(node["id"]), 0) == 0 and node["nodeType"] != "user"]
        important = sorted(nodes, key=lambda item: degree.get(str(item["id"]), 0), reverse=True)[:5]
        strong_edges = sorted(edges, key=lambda item: item["strength"], reverse=True)[:5]
        return [
            *[
                {
                    "type": "important_context",
                    "title": item["title"],
                    "detail": f"Connected to {degree.get(str(item['id']), 0)} related item(s).",
                    "nodeId": str(item["id"]),
                }
                for item in important
                if degree.get(str(item["id"]), 0) > 1
            ],
            *[
                {
                    "type": "hidden_dependency",
                    "title": node_by_id.get(str(edge["sourceNodeId"]), {}).get("title", "Connected work"),
                    "detail": f"Related to {node_by_id.get(str(edge['targetNodeId']), {}).get('title', 'another item')}: {edge['reason']}",
                    "nodeId": str(edge["sourceNodeId"]),
                }
                for edge in strong_edges
                if edge["relationshipType"] in {"related_to", "blocks", "influences", "depends_on"}
            ],
            *[
                {
                    "type": "forgotten_connection",
                    "title": item["title"],
                    "detail": "This item has no graph relationships yet.",
                    "nodeId": str(item["id"]),
                }
                for item in isolated[:3]
            ],
        ][:8]

    async def context_for_query(self, user_id: UUID, query: str, *, limit: int = 12) -> GraphContextOut:
        graph = await self.refresh(user_id)
        nodes = graph["nodes"]
        edges = graph["edges"]
        node_by_id = {str(node["id"]): node for node in nodes}
        tokens = self._keywords(query)
        scored_nodes = sorted(
            (
                (self._score(tokens, f"{node['title']} {node.get('description', '')}"), node)
                for node in nodes
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        seed_nodes = [node for score, node in scored_nodes if score > 0][:5]
        if not seed_nodes:
            seed_nodes = [node for node in nodes if node["nodeType"] in {"goal", "project"}][:4]
        seed_ids = {str(node["id"]) for node in seed_nodes}

        connected: list[GraphContextItemOut] = []
        for edge in sorted(edges, key=lambda item: item["strength"], reverse=True):
            source_id = str(edge["sourceNodeId"])
            target_id = str(edge["targetNodeId"])
            if source_id not in seed_ids and target_id not in seed_ids and not self._query_wants_edge(query, edge["relationshipType"]):
                continue
            other_id = target_id if source_id in seed_ids else source_id
            node = node_by_id.get(other_id) or node_by_id.get(source_id)
            if not node:
                continue
            connected.append(self._context_item(node, edge))
            if len(connected) >= limit:
                break

        blockers = [item for item in connected if item.relationshipType == "blocks" or item.nodeType == "open_loop"][:6]
        supporting = [item for item in connected if item.relationshipType in {"supports", "depends_on", "related_to", "created_from"}][:6]
        decisions = [item for item in connected if item.nodeType == "decision" or item.relationshipType == "influences"][:6]
        next_actions = [item for item in connected if item.nodeType in {"task", "open_loop", "project"}][:6]
        return GraphContextOut(
            query=query,
            currentEntities=[self._context_item(node, {"relationshipType": "related_to", "reason": "Matched the question.", "strength": 0.7}) for node in seed_nodes[:6]],
            blockers=blockers,
            supportingContext=supporting,
            decisions=decisions,
            nextActions=next_actions,
        )

    async def answer(self, user_id: UUID, question: str) -> GraphAnswerOut:
        context = await self.context_for_query(user_id, question)
        lower = question.casefold()
        if "block" in lower:
            evidence = context.blockers
            if evidence:
                answer = "Your clearest blockers are " + "; ".join(item.title for item in evidence[:4]) + "."
            else:
                answer = "I do not see a graph blocker yet. Refresh the graph after adding open loops or blocked tasks."
        elif "connected" in lower or "related" in lower:
            evidence = [item for item in [*context.currentEntities, *context.supportingContext] if item.nodeType == "project"][:6]
            answer = "Connected projects: " + ("; ".join(item.title for item in evidence) if evidence else "none visible yet.")
        elif "decision" in lower or "affected" in lower or "outcome" in lower:
            evidence = context.decisions
            answer = "Relevant decisions: " + ("; ".join(item.title for item in evidence[:5]) if evidence else "none connected yet.")
        else:
            evidence = context.nextActions or context.blockers or context.supportingContext
            answer = "Work next on " + (evidence[0].title if evidence else "the most active goal or project after refreshing the graph") + "."
        return GraphAnswerOut(question=question, answer=answer, evidence=evidence[:8])

    async def get_edge(self, user_id: UUID, edge_id: UUID) -> RelationshipEdge:
        result = await self.session.execute(
            select(RelationshipEdge).where(RelationshipEdge.id == edge_id, RelationshipEdge.user_id == user_id)
        )
        edge = result.scalar_one_or_none()
        if not edge:
            raise NotFoundError("Relationship edge not found")
        return edge

    async def create_edge(self, user_id: UUID, data: RelationshipEdgeCreate) -> dict:
        await self.get_node(user_id, data.sourceNodeId)
        await self.get_node(user_id, data.targetNodeId)
        edge = RelationshipEdge(
            user_id=user_id,
            source_node_id=data.sourceNodeId,
            target_node_id=data.targetNodeId,
            relationship_type=data.relationshipType.strip(),
            reason=data.reason.strip(),
            strength=data.strength,
        )
        self.session.add(edge)
        await self.session.flush()
        return self._edge_out(edge)

    async def update_edge(self, user_id: UUID, edge_id: UUID, data: RelationshipEdgeUpdate) -> dict:
        edge = await self.get_edge(user_id, edge_id)
        if data.relationshipType is not None:
            edge.relationship_type = data.relationshipType.strip()
        if data.reason is not None:
            edge.reason = data.reason.strip()
        if data.strength is not None:
            edge.strength = data.strength
        edge.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return self._edge_out(edge)

    async def delete_edge(self, user_id: UUID, edge_id: UUID) -> None:
        await self.session.delete(await self.get_edge(user_id, edge_id))

    async def neighborhood(self, user_id: UUID, node_id: UUID) -> dict:
        node = await self.get_node(user_id, node_id)
        edge_result = await self.session.execute(
            select(RelationshipEdge).where(
                RelationshipEdge.user_id == user_id,
                or_(RelationshipEdge.source_node_id == node_id, RelationshipEdge.target_node_id == node_id),
            )
        )
        edges = list(edge_result.scalars())
        related_ids = {
            edge.target_node_id if edge.source_node_id == node_id else edge.source_node_id
            for edge in edges
        }
        nodes: list[RelationshipNode] = []
        if related_ids:
            node_result = await self.session.execute(
                select(RelationshipNode).where(RelationshipNode.user_id == user_id, RelationshipNode.id.in_(related_ids))
            )
            nodes = list(node_result.scalars())
        return {
            "node": self._node_out(node),
            "relatedNodes": [self._node_out(item) for item in nodes],
            "edges": [self._edge_out(item) for item in edges],
        }

    async def _person_edges(self, user_id: UUID, node, edge, sources, project_nodes: dict[UUID, RelationshipNode]) -> None:
        person_mentions: Counter[str] = Counter()
        source_text: list[tuple[object, str, UUID | None]] = []
        for item in sources:
            text = " ".join(
                str(part)
                for part in (
                    getattr(item, "title", None),
                    getattr(item, "summary", None),
                    getattr(item, "content", None),
                    getattr(item, "description", None),
                    getattr(item, "active_intent", None),
                )
                if part
            )
            if not text:
                continue
            names = self._people(text)
            if not names:
                continue
            project_id = getattr(item, "project_id", None)
            source_text.append((item, text, project_id))
            person_mentions.update(names)

        for person_name, count in person_mentions.items():
            if count < 1:
                continue
            person_node = await node("person", None, person_name, "Person mentioned in workspace context.")
            await edge(person_node, await node("user", None, "You", "Workspace owner"), "related_to", "This person appears in your workspace context.", min(0.55 + count * 0.08, 0.88))
            for _, text, project_id in source_text:
                if person_name not in text or not project_id or project_id not in project_nodes:
                    continue
                await edge(person_node, project_nodes[project_id], "influences", f"{person_name} appears in context for this project.", 0.62)

    @staticmethod
    def _people(text: str) -> list[str]:
        candidates = re.findall(r"\b(?:with|from|for|by|customer|client|founder|user)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
        stop = {"Synzept", "Project", "Goal", "Decision", "Open Loop", "Founder Dashboard"}
        seen: set[str] = set()
        people: list[str] = []
        for candidate in candidates:
            clean = candidate.strip()
            if clean in stop or clean.casefold() in seen:
                continue
            seen.add(clean.casefold())
            people.append(clean)
        return people[:8]

    async def _keyword_edges(self, user_id: UUID) -> None:
        nodes = await self.list_nodes(user_id)
        existing = {
            (str(edge.source_node_id), str(edge.target_node_id), edge.relationship_type)
            for edge in await self.list_edges(user_id)
        }
        for index, left in enumerate(nodes):
            left_words = self._keywords(f"{left.title} {left.description}")
            if len(left_words) < 2:
                continue
            for right in nodes[index + 1:]:
                if left.node_type == right.node_type:
                    continue
                shared = sorted(left_words & self._keywords(f"{right.title} {right.description}"))
                if len(shared) < 2:
                    continue
                key = (str(left.id), str(right.id), "related_to")
                reverse_key = (str(right.id), str(left.id), "related_to")
                if key in existing or reverse_key in existing:
                    continue
                self.session.add(
                    RelationshipEdge(
                        user_id=user_id,
                        source_node_id=left.id,
                        target_node_id=right.id,
                        relationship_type="related_to",
                        reason=f"Both mention {', '.join(shared[:3])}.",
                        strength=min(0.55 + len(shared) * 0.08, 0.85),
                    )
                )

    async def _projects(self, user_id: UUID) -> list[Project]:
        return list((await self.session.execute(select(Project).where(Project.user_id == user_id, Project.deleted_at.is_(None)).limit(80))).scalars())

    async def _goals(self, user_id: UUID) -> list[Goal]:
        return list((await self.session.execute(select(Goal).where(Goal.user_id == user_id, Goal.deleted_at.is_(None)).limit(80))).scalars())

    async def _tasks(self, user_id: UUID) -> list[Task]:
        return list((await self.session.execute(select(Task).where(Task.user_id == user_id, Task.deleted_at.is_(None)).limit(120))).scalars())

    async def _notes(self, user_id: UUID) -> list[Note]:
        return list((await self.session.execute(select(Note).where(Note.user_id == user_id, Note.deleted_at.is_(None)).limit(120))).scalars())

    async def _memories(self, user_id: UUID) -> list[Memory]:
        return list((await self.session.execute(select(Memory).where(Memory.user_id == user_id, Memory.deleted_at.is_(None)).limit(120))).scalars())

    async def _conversations(self, user_id: UUID) -> list[Conversation]:
        return list((await self.session.execute(select(Conversation).where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None), Conversation.archived_at.is_(None)).limit(80))).scalars())

    async def _decisions(self, user_id: UUID) -> list[Decision]:
        return list((await self.session.execute(select(Decision).join(Project, Project.id == Decision.project_id).where(Project.user_id == user_id, Project.deleted_at.is_(None)).limit(120))).scalars())

    async def _legacy_decisions(self, user_id: UUID) -> list[ProjectDecision]:
        return list((await self.session.execute(select(ProjectDecision).join(Project, Project.id == ProjectDecision.project_id).where(Project.user_id == user_id, Project.deleted_at.is_(None)).limit(80))).scalars())

    async def _open_loops(self, user_id: UUID) -> list[OpenLoop]:
        return list((await self.session.execute(select(OpenLoop).join(Project, Project.id == OpenLoop.project_id).where(Project.user_id == user_id, Project.deleted_at.is_(None)).limit(120))).scalars())

    async def _legacy_open_loops(self, user_id: UUID) -> list[ProjectOpenLoop]:
        return list((await self.session.execute(select(ProjectOpenLoop).join(Project, Project.id == ProjectOpenLoop.project_id).where(Project.user_id == user_id, Project.deleted_at.is_(None)).limit(80))).scalars())

    async def _timeline(self, user_id: UUID) -> list[TimelineEvent]:
        return list((await self.session.execute(select(TimelineEvent).where(TimelineEvent.user_id == user_id).limit(120))).scalars())

    @staticmethod
    def _node_out(node: RelationshipNode) -> dict:
        return {
            "id": node.id,
            "userId": node.user_id,
            "nodeType": node.node_type,
            "entityId": node.entity_id,
            "title": node.title,
            "description": node.description or "",
            "createdAt": node.created_at,
            "updatedAt": node.updated_at,
        }

    @staticmethod
    def _edge_out(edge: RelationshipEdge) -> dict:
        return {
            "id": edge.id,
            "userId": edge.user_id,
            "sourceNodeId": edge.source_node_id,
            "targetNodeId": edge.target_node_id,
            "relationshipType": edge.relationship_type,
            "reason": edge.reason or "",
            "strength": edge.strength,
            "createdAt": edge.created_at,
            "updatedAt": edge.updated_at,
        }

    @staticmethod
    def _context_item(node: dict, edge: dict) -> GraphContextItemOut:
        return GraphContextItemOut(
            nodeId=node["id"],
            nodeType=node["nodeType"],
            title=node["title"],
            description=node.get("description", ""),
            relationshipType=edge.get("relationshipType", "related_to"),
            reason=edge.get("reason", ""),
            strength=edge.get("strength", 0.5),
        )

    @staticmethod
    def _score(tokens: set[str], value: str) -> float:
        if not tokens:
            return 0
        words = RelationshipGraphPhase5Service._keywords(value)
        if not words:
            return 0
        return len(tokens & words) / len(tokens)

    @staticmethod
    def _query_wants_edge(query: str, relationship_type: str) -> bool:
        text = query.casefold()
        return (
            ("block" in text and relationship_type == "blocks")
            or ("decision" in text and relationship_type == "influences")
            or ("next" in text and relationship_type in {"blocks", "supports", "depends_on"})
        )

    @staticmethod
    def _keywords(value: str) -> set[str]:
        stop = {"this", "that", "with", "from", "project", "task", "note", "decision", "memory", "knowledge", "conversation", "goal", "the", "and", "for", "what", "which", "next", "work"}
        return {item for item in re.findall(r"[a-z0-9]+", value.casefold()) if len(item) > 3 and item not in stop}
