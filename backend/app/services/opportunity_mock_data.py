MOCK_OPPORTUNITIES = [
    {
        "id": "opp-1",
        "title": "Double down on onboarding clarity",
        "category": "Growth",
        "summary": "The clearest leverage point is reducing setup friction so more users reach their first meaningful outcome.",
        "impact": "High",
        "effort": "Low",
        "urgency": "High",
        "confidence": "High",
        "score": 94,
        "expectedOutcome": "Higher activation and fewer users dropping after first setup.",
        "suggestedFirstAction": "Simplify the workspace setup screen and remove one optional decision.",
        "evidence": [
            "Onboarding completion currently sits around 63%.",
            "The workspace step shows the sharpest drop-off.",
            "Daily Brief adoption is strong and can carry the first-session value.",
        ],
        "source": "onboarding+activation"
    },
    {
        "id": "opp-2",
        "title": "Turn daily habits into momentum",
        "category": "Productivity",
        "summary": "A small daily review habit could turn the product from occasional tool into a repeatable operating system.",
        "impact": "High",
        "effort": "Medium",
        "urgency": "Medium",
        "confidence": "High",
        "score": 87,
        "expectedOutcome": "More consistent engagement and stronger retention over time.",
        "suggestedFirstAction": "Surface a one-minute daily review prompt after the first successful session.",
        "evidence": [
            "Users who reach the Daily Brief show stronger retention patterns.",
            "Habits are already present in the context graph.",
            "The product has strong potential as a recurring ritual.",
        ],
        "source": "habits+retention"
    },
    {
        "id": "opp-3",
        "title": "Surface the most useful memories earlier",
        "category": "Learning",
        "summary": "The memory layer is valuable but not yet obvious enough in the core flow.",
        "impact": "Medium",
        "effort": "Low",
        "urgency": "Medium",
        "confidence": "Medium",
        "score": 76,
        "expectedOutcome": "Users will trust the system more and recover context faster.",
        "suggestedFirstAction": "Show a memory prompt when a user revisits a project they last touched a week ago.",
        "evidence": [
            "Memories are connected to conversations and decisions in the graph.",
            "Users underuse search and chat, which suggests discoverability is the issue.",
        ],
        "source": "memory+context"
    },
    {
        "id": "opp-4",
        "title": "Create a stronger feedback loop around decisions",
        "category": "Startup",
        "summary": "Decision quality may be a major lever for future product direction and retention.",
        "impact": "Medium",
        "effort": "Medium",
        "urgency": "High",
        "confidence": "Medium",
        "score": 73,
        "expectedOutcome": "Better decision tracking and clearer learning from product experiments.",
        "suggestedFirstAction": "Prompt users to tie one decision to a mission or goal after a major workflow change.",
        "evidence": [
            "Decisions already connect to missions in the graph layer.",
            "A faster feedback loop should improve long-term product clarity.",
        ],
        "source": "decisions+mission"
    },
]

MOCK_OPPORTUNITY_HISTORY = [
    {"opportunityId": "opp-1", "status": "accepted", "note": "Simplify onboarding flow"},
    {"opportunityId": "opp-2", "status": "dismissed", "note": "Too much friction for now"},
]
