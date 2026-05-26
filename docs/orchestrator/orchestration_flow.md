# Orchestration Flow

The orchestrator is the central intelligence layer for chat, streaming, task creation, briefings, context retrieval, and memory scheduling.

## Main Entry Points

| Entry | Purpose |
|---|---|
| `Orchestrator.run` | non-streaming chat response |
| `Orchestrator.stream` | streaming chat response |
| `IntelligenceOrchestrator._prepare` | shared preparation path |

`app/orchestrator/pipeline.py` is a compatibility facade. `app/orchestrator/intelligence.py` owns the current pipeline.

## Request Flow

```text
Chat route
  -> Orchestrator
  -> IntelligenceOrchestrator
  -> ChatService.get_or_create
  -> ChatService.add_message(user)
  -> IntentClassifier
  -> PersonalizationEngine
  -> ConversationAnalyzer
  -> ContextEngine
  -> PromptAssembler
  -> LLMRouter
  -> ChatService.add_message(assistant)
  -> ActionAdvisor
  -> schedule_post_response
```

## Streaming Flow

`POST /api/v1/chat/stream` returns Server-Sent Events:

- `meta`: conversation id and intent
- `token`: partial assistant content
- `suggestions`: optional suggested actions
- `done`: completed conversation id
- `error`: safe error message

If a provider fails before tokens are emitted, the orchestrator falls back to non-streaming generation. If streaming is interrupted after tokens are emitted, partial content is preserved.

## AI Provider Rules

- All provider access goes through `LLMRouter`.
- Providers live in `app/services/providers`.
- Provider selection uses configured primary and fallback providers.
- AI interactions are logged through `AIInteractionLogger`.

## Prompt Safety

User input is sanitized before orchestration. If prompt-injection-like text appears, a system instruction is added to treat that text as user content only.

## Action Behavior

Task creation is only performed when the user explicitly requests a task. Suggestions are advisory and should not create work without user intent.
