MOCK_TIMELINE_EVENTS = [
    {
        "id": "tm-1",
        "kind": "mission",
        "title": "Started the Synzept prototype",
        "date": "2024-01-12",
        "summary": "The first internal mission centered on proving that personal context could accelerate action quality.",
        "tags": ["vision", "prototype"],
        "magnitude": "high",
        "confidence": 0.94,
        "context": "Early research and customer conversations",
        "outcome": "Validated a product hypothesis"
    },
    {
        "id": "tm-2",
        "kind": "decision",
        "title": "Chose a reflective, AI-first product direction",
        "date": "2024-03-08",
        "summary": "A decisive shift toward memory-driven workflows shaped the roadmap for the next six months.",
        "tags": ["product", "strategy"],
        "magnitude": "high",
        "confidence": 0.92,
        "context": "After seeing repeated friction in daily planning",
        "outcome": "Set the foundation for the current experience"
    },
    {
        "id": "tm-3",
        "kind": "project",
        "title": "Beta launch preparation",
        "date": "2024-06-29",
        "summary": "Planning milestones early helped the team reduce launch uncertainty and improve delivery rhythm.",
        "tags": ["launch", "delivery"],
        "magnitude": "medium",
        "confidence": 0.89,
        "context": "The team used a milestone-first rehearsal", 
        "outcome": "Improved confidence before the beta release"
    },
    {
        "id": "tm-4",
        "kind": "conversation",
        "title": "Customer feedback clarified the core value",
        "date": "2024-07-18",
        "summary": "User feedback made it clear that context and reflection were more important than raw automation.",
        "tags": ["feedback", "value"],
        "magnitude": "high",
        "confidence": 0.95,
        "context": "Interviewed early adopters and support users",
        "outcome": "Shifted messaging toward personal continuity"
    },
    {
        "id": "tm-5",
        "kind": "habit",
        "title": "Weekly review habit formed",
        "date": "2024-09-02",
        "summary": "Regular weekly reviews reduced rework and made decision-making more consistent.",
        "tags": ["habit", "reflection"],
        "magnitude": "medium",
        "confidence": 0.9,
        "context": "Reinforced with a lightweight ritual",
        "outcome": "Improved the quality of weekly decisions"
    },
    {
        "id": "tm-6",
        "kind": "memory",
        "title": "Captured the lessons from the first major setback",
        "date": "2024-11-14",
        "summary": "A major scope expansion exposed how quickly details can overwhelm execution.",
        "tags": ["lessons", "scope"],
        "magnitude": "high",
        "confidence": 0.91,
        "context": "Occurred after feature requests multiplied",
        "outcome": "Created a stronger prioritization posture"
    }
]

MOCK_TURNING_POINTS = [
    {
        "id": "tp-1",
        "title": "First paying customer",
        "date": "2024-05-21",
        "impact": "Created a stronger feedback loop and a sharper sense of urgency.",
        "whyItMatters": "It changed the focus from experimentation to sustainable product direction.",
        "confidence": 0.96
    },
    {
        "id": "tp-2",
        "title": "Beta launch",
        "date": "2024-08-03",
        "impact": "It turned a private hypothesis into a public learning system.",
        "whyItMatters": "Many future decisions were shaped by what users did after the launch.",
        "confidence": 0.94
    },
    {
        "id": "tp-3",
        "title": "Habit formation for weekly review",
        "date": "2024-09-02",
        "impact": "It reduced decision fatigue and improved follow-through.",
        "whyItMatters": "Small reflective rituals became a multiplier for larger outcomes.",
        "confidence": 0.9
    }
]

MOCK_REFLECTIONS = [
    {
        "id": "rf-1",
        "insight": "You make your best decisions after gathering customer feedback.",
        "evidence": ["Customer feedback clarified the core value", "Beta launch preparation"],
        "whyItMatters": "Your strongest choices tend to come from grounded signals rather than assumptions.",
        "confidence": 0.93
    },
    {
        "id": "rf-2",
        "insight": "You complete projects faster when you define milestones early.",
        "evidence": ["Beta launch preparation", "Started the Synzept prototype"],
        "whyItMatters": "Milestone clarity shortens ambiguity and improves momentum.",
        "confidence": 0.88
    },
    {
        "id": "rf-3",
        "insight": "Most delays came from expanding scope.",
        "evidence": ["Captured the lessons from the first major setback", "Chose a reflective, AI-first product direction"],
        "whyItMatters": "You gain speed when you protect focus and avoid unnecessary additions.",
        "confidence": 0.9
    }
]

MOCK_COMPARISONS = [
    {
        "id": "cmp-1",
        "label": "This month vs last month",
        "before": "More unstructured exploration and less emphasis on reflection.",
        "after": "A clearer rhythm of review, stronger priorities, and better follow-through.",
        "changes": ["Weekly review habit became consistent", "Decisions started to reference customer evidence"]
    },
    {
        "id": "cmp-2",
        "label": "Before vs after the beta launch",
        "before": "Roadmap thinking was more abstract and less grounded in behavior.",
        "after": "The product experience became more evidence-driven and user-informed.",
        "changes": ["Feedback loops became more visible", "Milestones improved delivery clarity"]
    }
]

MOCK_SEARCH_RESULTS = [
    {
        "id": "search-1",
        "title": "First paying customer",
        "kind": "turning-point",
        "date": "2024-05-21",
        "snippet": "A milestone that sharpened urgency and focused the direction of the product."
    },
    {
        "id": "search-2",
        "title": "Customer feedback clarified the core value",
        "kind": "conversation",
        "date": "2024-07-18",
        "snippet": "This event changed the way the product was explained and prioritized."
    },
    {
        "id": "search-3",
        "title": "Weekly review habit formed",
        "kind": "habit",
        "date": "2024-09-02",
        "snippet": "A repeatable ritual that improved consistency in decision-making."
    }
]
