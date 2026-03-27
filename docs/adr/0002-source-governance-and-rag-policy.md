# ADR 0002: Source Governance and RAG Policy

- Status: accepted
- Date: 2026-03-27

## Context

A learning product for 42-related preparation will inevitably encounter:

- official campus information
- community guides
- testers
- solution repositories
- AI-generated summaries

Without explicit governance, a retrieval system would drift toward unsafe answer generation and devalue learning.

## Decision

The product will enforce a tiered source policy.

Allowed tiers:

- `official_42`: ground truth
- `community_docs`: explanation and mapping
- `testers_and_tooling`: verification
- `solution_metadata`: path mapping only
- `blocked_solution_content`: blocked by default

The AI layer must respect this policy in retrieval and response generation.

## Consequences

Positive:

- preserves pedagogical integrity
- makes RAG behavior auditable
- clarifies what is authoritative versus interpretive
- allows community material without turning the app into a cheating tool

Negative:

- retrieval implementation becomes slightly more complex
- some users may perceive the assistant as more constrained than generic AI tools

## Rejected Alternatives

### Use all GitHub sources equally

Rejected because it collapses the distinction between explanation, verification and direct solution extraction.

### Ban community resources entirely

Rejected because testers, guides and community mapping are genuinely useful when governed properly.
