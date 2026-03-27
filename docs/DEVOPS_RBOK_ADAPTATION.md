# 42 Training DevOps Blueprint

## Goal

Adapt the strongest RBOK operational patterns to `42-training` without
overbuilding the repository too early.

This repository is still shell-first today, but the target product is a
triple-track learning app:

- Shell 0 to Hero
- C / Core 42
- Python + AI

The DevOps architecture must already anticipate:

- a web frontend
- an application API
- an AI / RAG service
- persistent learner state
- local-first development on Linux or WSL

## What To Reuse From RBOK

### Keep

- modular monolith mindset
- separated runtime units for `web`, `api`, `ai_gateway`
- `docker-compose` for local development
- `.env.example` per service
- CI jobs split by service
- build validation for containers
- documented health checks and smoke tests
- explicit separation between business API and AI orchestration

### Do Not Copy Blindly

- Jelastic-specific deployment assumptions
- RBAC and enterprise auth complexity
- mobile-specific flows
- infrastructure complexity that the app does not need yet

## Target Architecture

```text
42-training/
|-- apps/
|   `-- web/                 # Next.js frontend
|-- services/
|   |-- api/                 # FastAPI application API
|   `-- ai_gateway/          # RAG, prompt orchestration, AI tools
|-- packages/
|   |-- curriculum/          # Course graph, skill graph, rubrics
|   |-- mentor-engine/       # Mentor policies and prompts
|   `-- shared-types/        # Shared schemas and contracts
|-- docs/
|   `-- DEVOPS_RBOK_ADAPTATION.md
|-- infra/
|   `-- docker-compose.dev.example.yml
|-- prompts/
|-- scripts/
|-- progression.json
`-- README.md
```

## Runtime Model

### `apps/web`

- Next.js App Router
- consumes `api` and `ai_gateway`
- renders the 3 learning tracks
- no direct database access

### `services/api`

- FastAPI
- source of truth for learner profile, progression, curriculum state,
  checkpoints and evidence
- exposes REST endpoints first
- owns persistence

### `services/ai_gateway`

- FastAPI or lightweight Python service
- owns retrieval, prompt assembly and source filtering
- never becomes the source of truth for learner state
- enforces "no full solution by default" in foundation phases

### Shared stores

- PostgreSQL when the app becomes multi-screen and stateful
- Redis only when there is a real need for caching, rate limiting or
  session-like temporary state
- until then, JSON files remain acceptable for local prototyping

## Deployment Strategy

### Stage 1: Current repository

- shell scripts
- progression JSON
- mentor prompt
- no mandatory containers

### Stage 2: Local app foundation

- `web`, `api`, `ai_gateway`
- `docker-compose` for local development
- per-service `.env.example`
- smoke tests

### Stage 3: Hosted environments

- `develop`
- `staging`
- `main`

Git flow should mirror RBOK:

- feature branches -> PR
- merge to `develop`
- promote to `staging`
- controlled release to `main`

## CI/CD Model

Service-split pipelines, inspired by RBOK:

### Web CI

- install dependencies
- lint
- typecheck
- tests
- build

### API CI

- install dependencies
- lint
- tests
- smoke import / app boot
- container build

### AI Gateway CI

- install dependencies
- tests
- prompt/rag policy tests
- container build

## Health Checks

Every future service should expose a health endpoint:

- `web`: build/start health
- `api`: `/health`
- `ai_gateway`: `/health`

Smoke checks should verify:

- API boots
- web can reach API
- AI gateway can reach API
- source policy prevents solution dumping in foundation mode

## Environment Variables

Keep the RBOK habit of explicit env files, but stay smaller:

### Root

- `APP_ENV`
- `LOG_LEVEL`

### Web

- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_AI_GATEWAY_URL`

### API

- `API_PORT`
- `DATABASE_URL`
- `REDIS_URL`
- `APP_SECRET_KEY`

### AI Gateway

- `AI_GATEWAY_PORT`
- `AI_GATEWAY_API_BASE_URL`
- `OPENAI_API_KEY`
- `EMBEDDING_PROVIDER`
- `VECTOR_STORE_URL`

## RAG Policy

RBOK has a dedicated AI gateway. Keep that pattern here.

The RAG service must distinguish sources by usage policy:

- official 42 source
- community documentation
- tester/tooling
- solution metadata only
- blocked as direct answer material

This is a product rule and an infrastructure rule.

## Operational Rules

- never make the AI gateway the system of record
- never let solution repositories become unrestricted answer sources
- never couple web directly to storage
- always ship `.env.example`
- always keep local development Linux-first
- always keep smoke tests simple and fast

## Immediate Next Step

Create the future app directories and keep the current shell-first workflow
running in parallel until the app foundation exists.
