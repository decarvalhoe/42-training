# ADR 0004: JSON-First Progression State Before Database Migration

- Status: accepted
- Date: 2026-03-27

## Context

The repository already had a working shell-first workflow based on `progression.json`.
At the same time, the product is moving toward a richer application backend.

A direct migration to PostgreSQL at the very beginning would slow down iteration.

## Decision

The MVP keeps `progression.json` as the current learner-state source while exposing it through the API.

The backend architecture is prepared for a later migration to database-backed persistence, but the initial implementation stays JSON-first.

## Consequences

Positive:

- preserves continuity with the original repository
- keeps the MVP easy to run locally
- avoids premature persistence complexity
- allows faster iteration on the learning model

Negative:

- state management is limited
- concurrent editing semantics are weak
- future migration work remains necessary

## Rejected Alternatives

### Immediate PostgreSQL migration

Rejected because the product is still validating its learning model and service boundaries.

### Stay permanently file-based

Rejected because the long-term product will need richer persistence, queryability and user/session modeling.
