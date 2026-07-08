# Synzept V2 Life Graph Engine

## Graph data model

- Entity types: Mission, Goal, Project, Task, Note, Memory, Conversation, Person, Company, Event, Decision, Document, File, Meeting, Habit, Insight.
- Relationships: belongs_to, created_from, depends_on, references, related_to, mentioned_in, discussed_with, blocks, completed_by, inspired_by.
- Relationships are directional and queryable.

## Backend services

- RelationshipInferenceService: infers links from known patterns such as task-to-project and memory-to-conversation.
- GraphIntelligenceService: surfaces explainability, hidden connections, missing-link recommendations, and duplicate detection.
- LifeGraphService: orchestrates exploration, filtering, adjacency, and path generation with mock data.

## APIs

- GET /api/internal/life-graph/explore

## Mock data

- Mock entities and relationship links are seeded in the service layer.

## Graph Explorer UI

- Search by entity title.
- Filter by type.
- Browse visible graph nodes.
- Inspect relationship paths.

## Reusable components

- The page is composed of modular sections for search, filtering, node listing, and path display.

## Tests

- A backend test validates that exploration returns entities and relationships.
