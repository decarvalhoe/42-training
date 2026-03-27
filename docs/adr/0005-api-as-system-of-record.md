# ADR 0005: API as the Application System of Record

- Status: accepted
- Date: 2026-03-27

## Context

The product now includes a web layer, an API layer and an AI gateway.
A central decision is required on where application truth lives.

Without a clear decision, learner state, curriculum state and assistant outputs could become mixed together across layers.

## Decision

`services/api` is the application system of record.

It owns:

- learner progression state
- curriculum-serving endpoints
- future persistence logic
- future evidence and checkpoint modeling

The AI gateway may consume and enrich context, but it does not own application truth.

## Consequences

Positive:

- state remains auditable and deterministic
- assistant outputs do not silently redefine product truth
- the frontend has one authoritative application backend
- future persistence migration remains coherent

Negative:

- some interactions require explicit contracts between API and AI gateway
- short-term duplication of read models may appear during growth

## Rejected Alternatives

### Frontend as the state center

Rejected because state governance and policy enforcement belong server-side.

### AI layer as the truth source

Rejected because generated output is not a stable source of record.
