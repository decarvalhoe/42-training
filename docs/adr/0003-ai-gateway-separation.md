# ADR 0003: AI Gateway Separation

- Status: accepted
- Date: 2026-03-27

## Context

The product needs AI-assisted behaviors such as:

- mentor answers
- source-aware retrieval
- future reviewer or examiner roles

If AI logic is mixed directly into the application state layer, the repository risks:

- blurring product truth and generated output
- coupling persistence to model-specific behavior
- making guardrails harder to enforce

## Decision

AI concerns will be isolated in `services/ai_gateway`.

`services/api` remains the application system of record.

The AI gateway is responsible for:

- retrieval
- prompt assembly
- role orchestration
- source policy enforcement

The AI gateway is not responsible for owning learner truth or replacing the product backend.

## Consequences

Positive:

- clearer boundaries
- safer future RAG implementation
- easier testing of product state versus generated guidance
- easier replacement or refinement of AI behavior

Negative:

- one more runtime unit to maintain
- cross-service contracts must stay explicit

## Rejected Alternatives

### Put all AI logic inside the API service

Rejected because it would collapse product logic and assistant logic into one unstable layer.

### Let the frontend orchestrate AI behavior directly

Rejected because policy enforcement and source governance belong server-side.
