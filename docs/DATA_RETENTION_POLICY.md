# Data Retention, Minimisation & AI Journal Guardrails

## Purpose

Define retention, minimisation, and guardrail policies for AI-generated pedagogical journals (PedagogicalEvents, mentor interactions, defense sessions) to comply with privacy-by-design principles and protect learner data.

## Retention Policy

### Event Categories & TTL

| Event Type | Retention | Justification |
|---|---|---|
| `module_started` | 2 years | Progression tracking |
| `module_completed` | 2 years | Certification evidence |
| `checkpoint_submitted` | 1 year | Assessment records |
| `mentor_query` | 90 days | AI interaction audit trail |
| `defense_started` | 1 year | Evaluation records |

### Cleanup Strategy

- Daily cron job removes events past their TTL based on `created_at`
- Aggregated metrics (counts, averages) are preserved indefinitely
- Raw payload content (mentor prompts, learner answers) is the first data to be purged

## Minimisation Policy

### What We Collect

- Event type and timestamp (always)
- Learner ID and module context (always)
- Checkpoint index (when applicable)
- Source service identifier (always)

### What We Do NOT Collect

- Full mentor conversation history (only event count and metadata)
- Learner passwords or authentication tokens
- Raw LLM prompts/responses (only structured summaries)
- IP addresses or device fingerprints

### Payload Sanitisation

The `payload` JSON field on PedagogicalEvent must:
1. Never contain full solution code
2. Never contain raw LLM prompts longer than 200 characters
3. Never contain personally identifiable information beyond learner_id
4. Be validated at write time by `emit_event()` before persistence

## AI Journal Guardrails

### Mentor Interaction Logging

- Log: event type, learner_id, module_id, track_id, timestamp
- Log: response confidence level, sources_used count
- Do NOT log: full prompt text, full response text, learner input verbatim

### Defense Session Logging

- Log: session_id, questions asked (topics only), scores, timing
- Do NOT log: full answer text (only score and evaluation summary)

### Reviewer Interaction Logging

- Log: review request metadata, feedback category, score
- Do NOT log: full code snippet submitted (only language and line count)

## Implementation

### Phase 1 (Current)

- `emit_event()` already validates event_type against allowed literals
- Payload schema enforced by Pydantic `PedagogicalEventCreate`
- No full conversation logging implemented

### Phase 2 (Planned)

- Add TTL column to PedagogicalEvent model
- Implement cleanup management command: `python -m app.cleanup_events`
- Add payload size limit validation (max 4KB per event)
- Dashboard widget showing retention compliance status

### Phase 3 (Future)

- Automated anonymisation after retention period
- Export/delete API for GDPR-style data subject requests
- Audit log for data access and deletion operations

## Governance

- This policy is owned by the architecture/governance agent (claude)
- Changes require review by at least one other agent domain owner
- Policy is referenced from `CLAUDE.md` source-governance contract
