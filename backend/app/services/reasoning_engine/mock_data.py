MOCK_CONTEXT = [
    {
        "id": "ctx-current-mission",
        "type": "mission",
        "title": "Decision Intelligence foundation",
        "summary": "Synzept is building a reasoning-first layer that improves decisions before language generation.",
        "relevance": 0.91,
        "source": "workspace_home",
    },
    {
        "id": "ctx-sprint-1-dataset",
        "type": "pipeline",
        "title": "Sprint 1 Intelligence Dataset Pipeline",
        "summary": "Conversations are converted into reviewable goals, decisions, and tasks before graph save.",
        "relevance": 0.88,
        "source": "intelligence_dataset",
    },
]

MOCK_MEMORIES = [
    {
        "id": "mem-review-before-save",
        "type": "memory",
        "title": "Never auto-save high-impact knowledge",
        "summary": "High-impact extracted goals and decisions require user confirmation before persistence.",
        "relevance": 0.94,
        "source": "memory_feed",
    },
    {
        "id": "mem-llm-language-only",
        "type": "memory",
        "title": "LLM should generate language, not product decisions",
        "summary": "Planning and recommendation selection should happen in structured reasoning services.",
        "relevance": 0.96,
        "source": "product_principle",
    },
]

MOCK_KNOWLEDGE = [
    {
        "id": "kg-reasoning-first",
        "type": "knowledge",
        "title": "Reasoning-first architecture",
        "summary": "Separate intent, retrieval, evidence, risk, opportunity, and planning before response composition.",
        "relevance": 0.92,
        "source": "knowledge_graph",
    },
    {
        "id": "kg-user-approval-boundary",
        "type": "knowledge",
        "title": "Approval boundary",
        "summary": "Actions and durable knowledge changes require explicit user approval.",
        "relevance": 0.85,
        "source": "knowledge_graph",
    },
]

MOCK_DECISIONS = [
    {
        "id": "decision-review-before-graph-save",
        "type": "decision",
        "title": "Require review before graph save",
        "summary": "Extracted high-impact knowledge must be approved before it becomes a graph node.",
        "relevance": 0.89,
        "source": "decision_history",
    },
    {
        "id": "decision-modular-extractors",
        "type": "decision",
        "title": "Use independent extractors",
        "summary": "Goal, decision, and task extraction modules should be independently testable.",
        "relevance": 0.82,
        "source": "decision_history",
    },
]

MOCK_REQUESTS = [
    {
        "requestId": "reasoning-example-001",
        "userId": "mock-user",
        "message": "Should Synzept answer this user directly or ask for clarification before recommending the next product step?",
        "conversationId": "conv-reasoning-sprint-2",
        "metadata": {"surface": "workspace", "importance": "high"},
    }
]
