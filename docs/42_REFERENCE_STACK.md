# 42 Training Reference Stack

## Purpose

This document defines the pedagogical and code-quality reference hierarchy for
`42-training`.

The goal is not to collapse every source into one bucket. The goal is to keep a
clear order of authority:

1. official public 42 material
2. verified mirrors of official documents
3. tooling used to pre-check work
4. community explanations and mappings

This is especially important because the product now needs to support both:

- the historical C-heavy Common Core
- the emerging Python and AI lane seen in Lausanne signals and mirrored subject packs

## Absolute References

### Public official sources

- 42 Lausanne pedagogy page
- 42 Lausanne AI page
- The Norm v4.1
- the official `42school/norminette` repository

These sources define the top-level truth model for pedagogy, code quality and
language expectations where they are explicit.

### Verified mirrors of official documents

Two private reference repositories are now available locally for research:

- `Ninjarsenic/42-piscine`
- `Ninjarsenic/42-Tronc_commun`

They should be treated as mirrors of official subject packs and support files,
not as public official publication endpoints.

Practical rule:

- if the mirrored file is clearly an official PDF or support asset, it can be used
  as ground truth
- if origin is unclear, keep the source as `medium` confidence until corroborated

## Quality Stack

### C

For C, the reference stack is strict and ordered:

1. The Norm v4.1
2. norminette
3. project-specific testers
4. evaluator review and oral defense

Important nuance:

- norminette checks many objective rules
- it does not check every subjective or starred rule in the Norm
- evaluator review still matters for clarity, decomposition and readability

Key Norm constraints that matter product-wise:

- short functions
- limited parameters and local variables
- predictable formatting
- explicit declarations
- constrained macros and headers
- English-readable names
- no hidden global-state shortcuts

### francinette

Francinette is not an official 42 tool and its upstream is archived, but it is
still pedagogically useful because it models the broader pre-submit workflow.

Reverse-engineered behavior:

- detects the project from the folder and delivery artifacts
- copies code to a temp workspace
- runs `norminette`
- runs `make`
- dispatches to project-specific testers
- supports strict modes for memory allocation checks in some projects

This makes francinette useful as a verification harness, not as a source of
truth.

### mini-moulinette / mini-norminette variants

The exact campus naming is not fully canonical in public sources, but the tool
family is real and matches the role described by school discussion:

- very fast local pre-submit checks
- bundled exercise-level test cases
- score-like feedback that approximates a local moulinette

Use these tools as quick verification aids, never as the pedagogical authority.

## Python and Bash Equivalence

Python and Bash should not imitate the C Norm at the syntax level. They should
match it in spirit:

- explicitness
- small understandable units
- limited hidden behavior
- readable naming
- observable test coverage
- easy debugging

### Python equivalent

Recommended baseline:

- `ruff check`
- `ruff format`
- `mypy`
- `pytest`

What this replaces conceptually:

- Norm formatting discipline -> formatter and lint baseline
- limited implicit behavior -> typed boundaries and simpler functions
- evaluator readability pressure -> explicit data flow and testable behavior

### Bash equivalent

Recommended baseline:

- `shellcheck`
- `shfmt`
- smoke scripts or `bats`

What this replaces conceptually:

- Norm formatting discipline -> `shfmt`
- constrained syntax and clarity -> ShellCheck plus quoting discipline
- reviewer pressure -> readable pipelines, explicit error handling and debuggable scripts

## Curriculum Interpretation Policy

The new Common Core naming visible in the infographic and mirrored documents must
stay explicitly labeled as interpreted whenever public official publication is
still incomplete.

Rules:

- keep legacy C/Common Core projects as first-class references
- expose emerging Python and AI milestones with confidence labels
- never present inferred project names as fully canonical without saying so

## Product Impact

The application should surface:

- official references
- mirror references with confidence levels
- the quality stack per language
- the distinction between truth, verification and interpretation

This lets the learner train for the old and new tracks at the same time without
losing the original 42 rigor.
