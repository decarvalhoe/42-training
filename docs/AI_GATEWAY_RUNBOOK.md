# AI Gateway — Operator Runbook

> Operational reference for deploying, configuring, monitoring and troubleshooting the AI gateway service.

---

## Table of contents

1. [Architecture overview](#architecture-overview)
2. [Configuration](#configuration)
3. [Deployment](#deployment)
4. [Monitoring](#monitoring)
5. [Troubleshooting](#troubleshooting)
6. [Maintenance procedures](#maintenance-procedures)

---

## Architecture overview

### Service identity

| Property | Value |
|----------|-------|
| Service | `ai_gateway` |
| Framework | FastAPI 0.115.6 + Uvicorn 0.34.0 |
| Language | Python 3.13 |
| Default port | 8100 |
| Health endpoint | `GET /health` |

### Role in the system

The AI gateway is the **pedagogical intelligence layer**. It sits between the web frontend and the backend API, handling all LLM-powered interactions while enforcing source governance and learning contracts.

```
┌──────────┐     ┌──────────────┐     ┌──────────┐     ┌────────────┐
│ apps/web │────>│ ai_gateway   │────>│ Anthropic │     │            │
│          │     │ :8100        │     │ Claude API│     │ curriculum │
└──────────┘     │              │────>│           │     │ JSON data  │
                 │  - mentor    │     └───────────┘     └────────────┘
                 │  - librarian │
                 │  - reviewer  │────> ┌──────────┐
                 │  - examiner  │     │ services/ │
                 │  - intent    │────>│ api :8000 │
                 └──────────────┘     └──────────┘
```

### Agent roles

| Role | Endpoint | Purpose |
|------|----------|---------|
| **Intent router** | `POST /api/v1/intent` | Classifies learner messages and routes to the correct agent |
| **Mentor** | `POST /api/v1/mentor/respond` | Pedagogical guidance (observation, question, hint, next action) |
| **Librarian** | `POST /api/v1/librarian/search` | Source-governed resource discovery with tier filtering |
| **Reviewer** | `POST /api/v1/reviewer/review` | Code review with guardrails — never provides corrected code |
| **Examiner** | `POST /api/v1/defense/start`, `/answer`, `/{id}/result` | Oral defense simulation with scoring |

### External dependencies

| Dependency | Address | Required | Timeout |
|------------|---------|----------|---------|
| Anthropic Claude API | `api.anthropic.com` | Yes (for LLM features) | Default SDK |
| Backend API | `AI_GATEWAY_API_BASE_URL` (default `http://localhost:8000`) | Yes (for persistence) | 2.0s defense, 0.5s events |
| Curriculum data | Local filesystem (bundled in Docker image) | Yes | N/A |

### Key design decisions

- **Stateless**: No database — all persistent state lives in the backend API.
- **Graceful degradation**: LLM failures trigger hardcoded fallback responses.
- **Source governance**: Tier-based policy prevents solution leakage in early learning phases.
- **Pedagogical contract**: Mentor always returns 4-field structure; reviewer never provides corrected code.

Related ADRs: `docs/adr/0002-source-governance-and-rag-policy.md`, `docs/adr/0003-ai-gateway-separation.md`, `docs/adr/0006-multi-agent-role-model-and-orchestration.md`.

---

## Configuration

### Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | **Yes** | — | Claude API key for mentor and intent classification |
| `AI_GATEWAY_API_BASE_URL` | No | `http://localhost:8000` | Backend API base URL for persistence and events |
| `AI_GATEWAY_PORT` | No | `8100` | Port the gateway listens on |
| `DATA_ROOT` | No | Auto-detect | Root path for curriculum data files (set to `/` in Docker) |
| `OPENAI_API_KEY` | No | — | Reserved for future embedding support |
| `EMBEDDING_PROVIDER` | No | `openai` | Reserved for future vector store |
| `VECTOR_STORE_URL` | No | `http://localhost:6333` | Reserved for future Qdrant integration |

### Configuration template

See `services/ai_gateway/.env.example` for a copy-ready template.

### Data files

The gateway reads these files at startup (LRU-cached):

| File | Content | Mount path in Docker |
|------|---------|---------------------|
| `packages/curriculum/data/42_lausanne_curriculum.json` | Track definitions, modules, source policy | `/packages/curriculum/data/42_lausanne_curriculum.json` |
| `progression.json` | Learner progression schema | `/progression.json` |

### CORS

CORS is enabled with permissive defaults (`allow_origins=["*"]`, `allow_credentials=True`). For production, restrict `allow_origins` to the web frontend domain.

### LLM model

The gateway uses `claude-sonnet-4-20250514` with `temperature=0` and `max_tokens=1024`. These are set in `app/llm_client.py`.

---

## Deployment

### Docker (recommended)

```bash
# Build and start with docker compose
docker compose up ai_gateway

# Build only
docker compose build ai_gateway

# View logs
docker compose logs -f ai_gateway
```

The `docker-compose.yml` service definition:

```yaml
ai_gateway:
  build:
    context: .
    dockerfile: services/ai_gateway/Dockerfile
  environment:
    AI_GATEWAY_PORT: 8100
    AI_GATEWAY_API_BASE_URL: http://api:8000
    DATA_ROOT: /
  depends_on:
    api:
      condition: service_healthy
  ports:
    - "8100:8100"
```

**Dependencies**: The gateway requires the `api` service to be healthy before starting.

### Local development

```bash
cd services/ai_gateway
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key"

# Run tests
pytest tests -q

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload
```

### CI/CD pipeline

The CI pipeline (`.github/workflows/ci.yml`) runs:

1. **Lint**: `ruff check services/ai_gateway`
2. **Format**: `ruff format --check`
3. **Type check**: `mypy app`
4. **Unit tests**: `pytest tests -q`
5. **Smoke test**: Docker compose health check across all services

After a PR merges to `develop`, CI auto-deploys to the DEV environment.

### Docker health check

The Dockerfile includes a built-in health check:

```
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8100/health')" || exit 1
```

---

## Monitoring

### Health check

```bash
curl http://localhost:8100/health
# Expected: {"status":"ok","service":"ai_gateway"}
```

Any non-200 response or timeout indicates the service is unhealthy.

### Key signals to watch

| Signal | Where to look | Meaning |
|--------|--------------|---------|
| Health check failures | Docker health / orchestrator | Service is down or unresponsive |
| `WARNING` logs from `main.py` | Container stdout | LLM call failed, using fallback |
| `WARNING` logs from `events.py` | Container stdout | Event forwarding to API failed (non-critical) |
| `INFO` logs from `defense_persistence.py` | Container stdout | Defense session lifecycle events |
| High response latency on `/mentor/respond` | Application logs / proxy | Claude API may be slow or rate-limited |
| `classifier: "fallback"` in intent responses | Application logs | LLM intent classification failed, using keyword fallback |
| `confidence_level: "low"` in mentor responses | Application logs | Low-confidence responses may indicate retrieval issues |

### Log format

The gateway uses Python's standard `logging` module. All modules log via `logging.getLogger(__name__)`. Logs go to stdout (captured by Docker).

### Suggested alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| Gateway down | Health check fails 3 consecutive times | P1 |
| LLM degraded | >50% of mentor responses use fallback in 5min window | P2 |
| API backend unreachable | Defense persistence errors sustained >2min | P2 |
| High latency | p95 response time >10s on mentor endpoint | P3 |

---

## Troubleshooting

### Gateway fails to start

**Symptom**: Container exits immediately or health check never passes.

**Check**:
```bash
docker compose logs ai_gateway
```

| Cause | Log signature | Fix |
|-------|--------------|-----|
| Missing `ANTHROPIC_API_KEY` | `RuntimeError: ANTHROPIC_API_KEY not set` | Set the env var in `.env` or docker-compose |
| Port conflict | `Address already in use` | Change `AI_GATEWAY_PORT` or stop conflicting process |
| Curriculum file missing | `FileNotFoundError` on curriculum JSON | Verify `DATA_ROOT` and that files are copied in Docker build |
| Backend API not ready | Health passes but defense/events fail | Check that `api` service is healthy at `AI_GATEWAY_API_BASE_URL` |

### Mentor returns hardcoded fallback instead of LLM response

**Symptom**: Every mentor response has identical structure regardless of question.

**Check**:
```bash
# Test LLM connectivity
curl -X POST http://localhost:8100/api/v1/mentor/respond \
  -H "Content-Type: application/json" \
  -d '{"question":"test","phase":"foundation"}'
```

| Cause | Fix |
|-------|-----|
| Invalid or expired API key | Rotate `ANTHROPIC_API_KEY` |
| Anthropic API rate limit | Check Anthropic dashboard; reduce request rate |
| Network connectivity | Verify outbound HTTPS to `api.anthropic.com` |
| JSON parse failure from LLM | Check logs for `ValueError` — may indicate model output format change |

### Intent classification always returns fallback

**Symptom**: `IntentResponse.classifier` is always `"fallback"`.

**Cause**: Same as mentor LLM issues above. The intent classifier uses the same Claude API.

**Fallback behavior**: Routes to `mentor` by default when LLM classification fails. The system remains functional but with reduced routing accuracy.

### Defense session errors

**Symptom**: `POST /api/v1/defense/start` returns 503.

**Check**:
```bash
# Test backend API connectivity
curl http://localhost:8000/health

# Check defense persistence
curl http://localhost:8000/api/v1/defense-sessions
```

| Cause | Fix |
|-------|-----|
| Backend API down | Restart `api` service |
| Backend API unreachable | Verify `AI_GATEWAY_API_BASE_URL` resolves from gateway container |
| Timeout (>2s) | Check backend API performance; increase timeout if needed |

### Reviewer guardrails scrubbing content

**Symptom**: `ReviewerResponse.guardrail_scrubbed_fields` is non-empty.

This is **expected behavior** — the reviewer detects and removes solution-leaking content in `foundation`, `practice`, and `core` phases. The `guardrail_clean` field indicates whether scrubbing occurred.

If scrubbing is too aggressive, check the regex patterns in `app/reviewer.py`.

### Events not reaching backend

**Symptom**: Pedagogical events missing from backend.

Event forwarding is **best-effort** with a 0.5s timeout. Failures are logged as warnings but do not affect the user-facing response.

**Check**: Look for `WARNING` logs from `events.py` in gateway output.

---

## Maintenance procedures

### Updating the curriculum

1. Edit `packages/curriculum/data/42_lausanne_curriculum.json`.
2. Rebuild the Docker image (the curriculum is copied at build time).
3. Restart the gateway — the LRU cache will reload on first request.

### Rotating the Anthropic API key

1. Generate a new key in the Anthropic console.
2. Update `ANTHROPIC_API_KEY` in the deployment environment.
3. Restart the gateway container.
4. Verify with a mentor request.

No downtime required — the gateway will use fallback responses during restart.

### Scaling considerations

The gateway is stateless and can be horizontally scaled. Key constraints:

- **Anthropic API rate limits**: Each instance shares the same API key quota.
- **Backend API load**: Each defense session generates multiple API calls.
- **In-memory defense sessions**: Active sessions live in process memory alongside API persistence. If an instance restarts mid-session, the session can be reloaded from the backend API.

### Running tests

```bash
cd services/ai_gateway

# All tests
pytest tests -q

# Specific module
pytest tests/test_defense.py -q

# With coverage
pytest tests --cov=app --cov-report=term

# Linting
ruff check app
ruff format --check app
mypy app
```

### Version matrix

| Component | Version |
|-----------|---------|
| Python | 3.13 |
| FastAPI | 0.115.6 |
| Uvicorn | 0.34.0 |
| anthropic | >= 0.39.0 |
| httpx | 0.28.1 |
| pydantic | 2.10.4 |
