# 42 Training Target Architecture

## Product Shape

One app, three tracks:

- `shell`
- `c`
- `python_ai`

One shared backend:

- progression
- curriculum graph
- mentor policy
- checkpoints
- source filtering

One separate AI unit:

- retrieval
- prompt assembly
- guarded assistance

## Why This Matches RBOK

Patterns reused from RBOK:

- modular monolith
- web + api + ai separation
- service-level CI
- container-first local runtime
- explicit environment contracts

Patterns intentionally not reused:

- enterprise auth stack
- heavy infra assumptions
- production topology complexity too early

## Build Order

1. Preserve the current shell-first mentor repo.
2. Add `apps/web`.
3. Add `services/api`.
4. Add `services/ai_gateway`.
5. Move curriculum and mentor logic into `packages/`.
6. Replace pure JSON-only progression with API-backed state when needed.
