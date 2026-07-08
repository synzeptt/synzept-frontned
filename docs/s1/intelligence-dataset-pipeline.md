# Sprint 1 Intelligence Dataset Pipeline

This sprint establishes the mock-first foundation for converting conversations into structured Synzept knowledge for Decision Intelligence.

## Core Object Model

`SynzeptObject` is the base object shape:

- `id`
- `type`
- `title`
- `summary`
- `confidence`
- `source`
- `createdAt`
- `updatedAt`
- `metadata`
- `relationships`

Initial object types:

- `goal`
- `decision`
- `task`

Relationships support `related_to`, `created_from`, `supports`, and `blocks`.

## Pipeline

Conversation input moves through modular stages:

1. Preprocessing
2. Goal extraction
3. Decision extraction
4. Task extraction
5. Confidence scoring
6. Review queue

Each extractor implements a small independent class and returns candidate `SynzeptObject` records. Future extractors can be added by implementing the same `extract(sentences, conversation)` interface and registering the class in `IntelligenceDatasetService`.

## Review Queue

Extracted objects are not automatically saved into the graph. They enter the review queue with:

- extracted object
- extractor name
- confidence
- impact
- rationale
- pending status

Users can approve, edit, or reject. Approval inserts the object into the mock knowledge graph. Rejection leaves the graph unchanged.

## Knowledge Graph

Approved objects become graph nodes. Relationships on approved objects are materialized as graph edges. Sprint 1 keeps graph storage in a mock in-memory repository-like service so future persistence can replace the implementation without changing the API contract.

## APIs

Base path: `/api/intelligence-dataset`

- `GET /sample-conversation`
- `POST /extract`
- `GET /review`
- `POST /review/{review_item_id}/approve`
- `POST /review/{review_item_id}/reject`
- `GET /graph`

## UI

The workspace screen is available at `/intelligence-dataset`.

It includes:

- extraction pipeline stages
- pending review queue
- approve, edit, and reject actions
- approved objects view
- graph relationship summary

## Quality

Tests cover:

- pipeline stage ordering
- extraction of goals, decisions, and tasks
- no auto-save before approval
- approval with edits
- rejection without graph insert
- graph relationship edge creation

This implementation uses mock data only and does not connect to production conversations or memory stores.
