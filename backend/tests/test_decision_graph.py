from app.services.decision_graph import DecisionGraphService


def test_decision_graph_contains_required_decision_node_fields():
    decisions = DecisionGraphService().decision_nodes()

    assert decisions
    assert all(node.id and node.title and node.description for node in decisions)
    assert all(node.timestamp and node.confidence is not None and node.status and node.importance for node in decisions)


def test_decision_graph_supports_required_relationship_types():
    graph = DecisionGraphService().graph()
    relationships = {edge.relationship for edge in graph.edges}

    assert {
        "influenced_by",
        "supports",
        "blocks",
        "resulted_in",
        "contradicts",
        "related_to",
        "learned_from",
    } <= relationships
    assert "reviewed_by" in graph.supportedRelationships


def test_node_neighborhood_returns_connected_context():
    graph = DecisionGraphService().node_neighborhood("decision-memory-feed-home")
    node_ids = {node.id for node in graph.nodes}

    assert "decision-memory-feed-home" in node_ids
    assert "goal-return-user-clarity" in node_ids
    assert graph.edges


def test_relationship_filter_returns_only_matching_edges():
    graph = DecisionGraphService().graph(relationship="supports")

    assert graph.edges
    assert all(edge.relationship == "supports" for edge in graph.edges)


def test_graph_chains_trace_cause_and_effect():
    chains = DecisionGraphService().chains()
    memory_chain = next(chain for chain in chains if chain.id == "chain-memory-feed-cause-effect")

    assert memory_chain.nodeIds[0] == "memory-context-visible"
    assert "decision-memory-feed-home" in memory_chain.nodeIds
    assert memory_chain.edgeIds


def test_graph_insights_reference_supporting_connections():
    insights = DecisionGraphService().insights()

    assert insights
    assert all(insight.supportingConnectionIds for insight in insights)
    assert insights[0].impact >= insights[-1].impact
