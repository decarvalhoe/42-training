# ADR 0008: Official Reference Stack and Cross-Language Quality Equivalence

- Status: accepted
- Date: 2026-03-29

## Context

`42-training` now has access to stronger pedagogical references than the initial MVP:

- The Norm v4.1 as the current official C standard
- mirrored repositories containing current official subject PDFs and exercise packs
- school feedback that real pre-submit practice often involves `norminette`, `francinette` and smaller local tester variants
- an emerging Python and AI common-core lane that should not erase the rigor of the legacy C path

The product therefore needs a stable decision on:

- what counts as absolute pedagogical truth
- what counts as verification tooling rather than truth
- how to translate the spirit of 42 code rigor into Python and Bash without pretending those languages should follow C syntax rules

## Decision

The product will adopt the following reference model:

- The Norm v4.1 is the absolute code-quality and pedagogical reference for C.
- Public 42 pages and official normative documents remain the highest-authority sources.
- Private or community-hosted mirrors of official documents are accepted as ground truth only when the mirrored origin is explicit and verified.
- `norminette` is treated as the official automated checker for the objective subset of the Norm, not as a full replacement for evaluator review.
- `francinette` and mini-moulinette or mini-norminette style tools are treated as verification harnesses, not as normative truth.
- Python and Bash tracks must use coherent quality equivalents:
  - Python: `ruff`, `mypy`, `pytest`, short explicit functions, typed boundaries, observable behavior
  - Bash: `shellcheck`, `shfmt`, shell smoke tests, explicit quoting, fail-fast habits, readable command composition

The application must expose this reference stack directly in its curriculum and UI so that pedagogy, source policy and quality expectations stay aligned.

## Consequences

Positive:

- preserves the historical 42 C rigor as a first-class reference
- makes the new Python lane compatible with the old standards in spirit rather than by superficial imitation
- distinguishes official truth from mirrors, testers and community guidance
- gives the UI and future RAG layers a stable model for confidence and tool recommendations

Negative:

- requires ongoing maintenance as the new curriculum becomes more public and less inferred
- creates a broader reference surface than the initial MVP
- some community tooling is archived or platform-fragile and must be presented with caveats

## Rejected Alternatives

### Treat all testers as authoritative

Rejected because testers approximate evaluation behavior but do not define the pedagogical standard.

### Reuse the C Norm verbatim for Python and Bash

Rejected because equivalent rigor matters more than syntactic mimicry.

### Ignore the emerging Python lane until the school publishes everything

Rejected because the product goal is explicitly to prepare for both the legacy and emerging Common Core shapes while keeping confidence levels visible.
