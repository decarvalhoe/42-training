# ADR 0007: PostgreSQL Migration Strategy After JSON-First MVP

- Status: accepted
- Date: 2026-03-27

## Context

The MVP intentionally keeps progression in `progression.json` for speed and continuity.
However, the long-term product will need stronger persistence for:

- multiple learners or learner profiles
- evidence and checkpoints
- richer querying
- source registries
- future RAG and evaluation logs

A migration strategy is needed before persistence grows organically and inconsistently.

## Decision

The product will move to PostgreSQL after the MVP learning model stabilizes.

Migration order:

1. learner profile and progression state
2. tracks, modules and checkpoint references
3. evidence and review artifacts
4. source registry and retrieval metadata
5. optional AI interaction logs with policy-safe storage

`progression.json` remains useful as a bootstrap and export format, not as the permanent core store.

## Consequences

Positive:

- preserves current iteration speed now
- gives a clear persistence roadmap later
- avoids ad hoc storage sprawl
- supports future analytics and richer workflows

Negative:

- migration work must still be planned and executed carefully
- temporary duplication may exist during the transition period

## Rejected Alternatives

### Stay indefinitely on JSON files

Rejected because the product will outgrow file-based state.

### Introduce PostgreSQL immediately for every concept

Rejected because the learning model is still being validated and should not be overconstrained too early.
