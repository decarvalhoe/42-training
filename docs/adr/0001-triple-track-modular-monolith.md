# ADR 0001: Triple-Track Modular Monolith

- Status: accepted
- Date: 2026-03-27

## Context

`42-training` started as a shell-first preparation workspace and evolved toward a product vision that includes:

- Shell 0 to Hero
- C / Core 42 preparation
- Python + AI preparation

The product also needs:

- a web UI
- an application backend
- an assistant layer
- future persistence and retrieval

A naive response would be either:

- three separate applications, one per track
- or a distributed microservice architecture from the start

Both options would create unnecessary fragmentation.

## Decision

The product will be built as one application with three learning tracks and a modular monolith architecture.

The runtime is separated into:

- `apps/web`
- `services/api`
- `services/ai_gateway`

Shared logic lives under `packages/`.

## Consequences

Positive:

- one coherent learning model
- one source policy
- one progression engine
- lower development and maintenance overhead
- easier future extraction if a boundary becomes stable

Negative:

- requires discipline to preserve boundaries inside one repository
- some early modules may feel under-separated until the product matures

## Rejected Alternatives

### Three independent apps

Rejected because the learner model, source policy and progression system are shared.

### Microservices from day one

Rejected because the product is still early and the complexity would exceed the real operational need.
