from app.schemas.intelligence_dataset import ConversationExtractIn, ReviewEditIn
from app.services.intelligence_dataset import IntelligenceDatasetService
from app.services.intelligence_dataset.mock_data import MOCK_CONVERSATION


def _service_with_extraction():
    service = IntelligenceDatasetService()
    result = service.extract(ConversationExtractIn(**MOCK_CONVERSATION))
    return service, result


def test_extract_pipeline_creates_review_items_without_auto_saving_to_graph():
    service = IntelligenceDatasetService()
    before_count = len(service.graph().nodes)

    result = service.extract(ConversationExtractIn(**MOCK_CONVERSATION))

    assert result.conversationId == MOCK_CONVERSATION["conversationId"]
    assert [stage.name for stage in result.stages] == [
        "preprocessing",
        "goal_extractor",
        "decision_extractor",
        "task_extractor",
        "review_queue",
    ]
    assert result.pendingReviewItems
    assert len(service.graph().nodes) == before_count


def test_each_initial_object_type_can_be_extracted():
    _, result = _service_with_extraction()
    object_types = {item.object.type for item in result.pendingReviewItems}

    assert {"goal", "decision", "task"}.issubset(object_types)


def test_review_items_can_be_approved_with_edits_into_graph():
    service, result = _service_with_extraction()
    review_item = result.pendingReviewItems[0]

    action = service.approve(review_item.id, ReviewEditIn(title="Edited approved object", metadata={"reviewedBy": "user"}))

    assert action.status == "approved"
    assert action.graphNode is not None
    assert action.graphNode.title == "Edited approved object"
    assert action.graphNode.metadata["reviewedBy"] == "user"
    assert any(node.id == action.graphNode.id for node in service.graph().nodes)


def test_review_items_can_be_rejected_without_graph_insert():
    service, result = _service_with_extraction()
    review_item = result.pendingReviewItems[-1]
    before_ids = {node.id for node in service.graph().nodes}

    action = service.reject(review_item.id)

    assert action.status == "rejected"
    assert {node.id for node in service.graph().nodes} == before_ids


def test_graph_contains_relationship_edges_for_approved_objects():
    service, result = _service_with_extraction()
    review_item = result.pendingReviewItems[0]

    service.approve(review_item.id)
    graph = service.graph()

    assert graph.nodes
    assert any(edge.type in {"created_from", "supports"} for edge in graph.edges)
