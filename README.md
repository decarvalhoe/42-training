# 42 Training

## FR

Espace de preparation Linux-first pour 42 Lausanne.

Le depot contient maintenant deux couches qui coexistent:

- le workflow historique centré terminal, shell et mentor
- une fondation MVP d'application pour une plateforme pedagogique a trois parcours

### Index documentaire

Documentation principale:

- `docs/RUNBOOK_LOCAL.md` — demarrage local en 3 commandes et depannage
- `docs/PRODUCT_METRICS.md` — KPIs produit et pedagogiques, SQL analytics et structure de dashboard
- `docs/JSON_TO_PG_MIGRATION.md` — design du pipeline d'import `progression.json` vers PostgreSQL et strategie de transition
- `docs/APPROCHE_ARCHITECTURE_EXHAUSTIVE.md`
- `docs/42_REFERENCE_STACK.md`
- `docs/NEW_TC_PROJECT_PREDICTIONS.md`
- `ARCHITECTURE_TARGET.md`
- `docs/DEVOPS_RBOK_ADAPTATION.md`
- `docs/adr/README.md`
- `AGENTS.md`
- `CLAUDE.md`

Documentation GitHub:

- `.github/CONTRIBUTING.md`
- `.github/SECURITY.md`
- `.github/SUPPORT.md`
- `.github/CODE_OF_CONDUCT.md`

### Direction produit

Le produit cible est une application unique avec trois parcours:

- `shell`: Shell 0 to Hero
- `c`: preparation low-level et logique 42
- `python_ai`: bases Python, IA, RAG et agents

L'architecture suit volontairement des patterns inspirés de RBOK:

- monolithe modulaire
- separation `web`, `api`, `ai_gateway`
- gouvernance explicite des sources
- developpement local scriptable et Linux-first

### Structure du depot

```text
42-training/
|-- apps/web/
|-- services/api/
|-- services/ai_gateway/
|-- packages/curriculum/
|-- packages/mentor-engine/
|-- packages/shared-types/
|-- scripts/
|-- progression.json
`-- docker-compose.yml
```

### Lancer le MVP en local

#### Option 1: Docker (recommande)

```bash
./scripts/dev-up.sh
```

Le script copie les `.env.example` si necessaire, demarre tous les services via docker-compose, attend les healthchecks et affiche les URLs.

Pour arreter:

```bash
docker compose down
```

#### Option 2: Sans Docker (services individuels)

API:

```bash
./scripts/start_api.sh
```

AI gateway:

```bash
./scripts/start_ai_gateway.sh
```

Web:

```bash
cd apps/web
npm install
cd ../..
./scripts/start_web.sh
```

Smoke test:

```bash
./scripts/smoke_mvp.sh
```

### Endpoints disponibles

API:

- `GET /health`
- `GET /api/v1/meta`
- `GET /api/v1/dashboard`
- `GET /api/v1/tracks`
- `GET /api/v1/tracks/{track_id}`
- `GET /api/v1/progression`
- `POST /api/v1/progression`

AI Gateway:

- `GET /health`
- `GET /api/v1/source-policy`
- `POST /api/v1/mentor/respond`

### Notes

- L'AI gateway est volontairement contraint: pas de solution complete par defaut dans les phases fondamentales.
- Les repos de solutions de la communaute sont traites comme sources de cartographie, pas comme materiau libre de reponse.
- Le frontend contient un fallback local afin de rester utile meme si l'API n'est pas encore demarree.

## EN

Linux-first preparation workspace for 42 Lausanne.

The repository now contains two coexisting layers:

- the historical shell-first mentor workflow
- a new MVP application foundation for a triple-track learning platform

### Documentation index

Core documentation:

- `docs/RUNBOOK_LOCAL.md` — 3-command local setup and troubleshooting
- `docs/PRODUCT_METRICS.md` — product and pedagogical KPIs, analytics SQL and dashboard structure
- `docs/JSON_TO_PG_MIGRATION.md` — initial `progression.json` to PostgreSQL import design and transition strategy
- `docs/APPROCHE_ARCHITECTURE_EXHAUSTIVE.md`
- `docs/42_REFERENCE_STACK.md`
- `docs/NEW_TC_PROJECT_PREDICTIONS.md`
- `ARCHITECTURE_TARGET.md`
- `docs/DEVOPS_RBOK_ADAPTATION.md`
- `docs/adr/README.md`
- `AGENTS.md`
- `CLAUDE.md`

GitHub health documentation:

- `.github/CONTRIBUTING.md`
- `.github/SECURITY.md`
- `.github/SUPPORT.md`
- `.github/CODE_OF_CONDUCT.md`

### Product direction

The target product is one application with three tracks:

- `shell`: Shell 0 to Hero
- `c`: low-level and core-42 preparation
- `python_ai`: Python foundations, AI, RAG and agent literacy

The architecture deliberately follows RBOK-inspired patterns:

- modular monolith
- `web`, `api` and `ai_gateway` separation
- explicit source governance
- scriptable local development with a Linux-first bias

### Repository layout

```text
42-training/
|-- apps/web/
|-- services/api/
|-- services/ai_gateway/
|-- packages/curriculum/
|-- packages/mentor-engine/
|-- packages/shared-types/
|-- scripts/
|-- progression.json
`-- docker-compose.yml
```

### Run the MVP locally

#### Option 1: Docker (recommended)

```bash
./scripts/dev-up.sh
```

The script copies `.env.example` files if needed, starts all services via docker-compose, waits for healthchecks and prints service URLs.

To stop:

```bash
docker compose down
```

#### Option 2: Without Docker (individual services)

API:

```bash
./scripts/start_api.sh
```

AI gateway:

```bash
./scripts/start_ai_gateway.sh
```

Web:

```bash
cd apps/web
npm install
cd ../..
./scripts/start_web.sh
```

Smoke test:

```bash
./scripts/smoke_mvp.sh
```

### Available endpoints

API:

- `GET /health`
- `GET /api/v1/meta`
- `GET /api/v1/dashboard`
- `GET /api/v1/tracks`
- `GET /api/v1/tracks/{track_id}`
- `GET /api/v1/progression`
- `POST /api/v1/progression`

AI Gateway:

- `GET /health`
- `GET /api/v1/source-policy`
- `POST /api/v1/mentor/respond`

### Notes

- The AI gateway is intentionally constrained: no full solution by default in foundation phases.
- Community solution repositories are treated as mapping sources, not as unrestricted answer material.
- The frontend ships with a local fallback dataset so it remains useful even before the API is running.
