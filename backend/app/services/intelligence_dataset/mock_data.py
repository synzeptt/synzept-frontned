MOCK_CONVERSATION = {
    "conversationId": "conv-sprint-1-dataset",
    "title": "Sprint 1 planning for Decision Intelligence",
    "transcript": """
    We need Synzept to turn conversations into structured knowledge without saving important objects automatically.
    Goal: establish a reliable intelligence dataset pipeline for Decision Intelligence.
    Decision: keep extracted goals, decisions, and tasks in a review queue before they enter the graph.
    Task: create independent extractors for goals, decisions, and tasks.
    Task: build an extraction review screen where users can approve, edit, or reject suggestions.
    This supports the Decision Intelligence Engine and blocks unsafe auto-save behavior.
    """,
    "source": "conversation",
    "metadata": {"workspace": "Synzept", "sprint": "Sprint 1", "importance": "high"},
}

MOCK_APPROVED_OBJECTS = [
    {
        "id": "goal-decision-intelligence-foundation",
        "type": "goal",
        "title": "Establish Decision Intelligence foundation",
        "summary": "Create a pipeline that converts conversations into reviewable structured knowledge.",
        "confidence": 0.89,
        "source": "conversation:conv-sprint-1-dataset",
        "createdAt": "2026-07-08T09:15:00+05:30",
        "updatedAt": "2026-07-08T09:15:00+05:30",
        "metadata": {"impact": "high", "sprint": "Sprint 1"},
        "relationships": [],
    },
    {
        "id": "decision-review-before-graph-save",
        "type": "decision",
        "title": "Require review before graph save",
        "summary": "Extracted high-impact knowledge must be approved before it becomes a graph node.",
        "confidence": 0.92,
        "source": "conversation:conv-sprint-1-dataset",
        "createdAt": "2026-07-08T09:18:00+05:30",
        "updatedAt": "2026-07-08T09:18:00+05:30",
        "metadata": {"status": "accepted", "impact": "high"},
        "relationships": [
            {
                "type": "supports",
                "targetId": "goal-decision-intelligence-foundation",
                "confidence": 0.86,
                "evidence": "Review gates protect quality and user trust.",
            }
        ],
    },
]
