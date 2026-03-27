# ADR 0006: Multi-Agent Role Model and Orchestration

- Status: accepted
- Date: 2026-03-27

## Context

The product direction includes AI-assisted learning features that exceed a single generic assistant persona.
Different interactions require different behaviors:

- guided help
- source retrieval
- review and critique
- oral-defense simulation
- orchestration across roles

A role model is needed before the orchestration layer grows.

## Decision

The long-term agent model will be structured around five roles:

- Mentor
- Librarian
- Reviewer
- Examiner
- Orchestrator

The AI gateway will be the natural home for this orchestration.

## Consequences

Positive:

- role boundaries stay explicit
- prompts and policies can be specialized per task
- pedagogical interactions become more predictable
- future UI can expose distinct workflows cleanly

Negative:

- orchestration logic adds product complexity
- role drift must be managed through documentation and testing

## Rejected Alternatives

### One universal assistant persona

Rejected because it blurs pedagogy, retrieval, review and defense behaviors into one unstable role.

### Many independent agent services from the start

Rejected because the product is still early and should keep orchestration centralized.
