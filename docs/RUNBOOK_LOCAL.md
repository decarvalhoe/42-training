# Runbook local / Local runbook

## FR

### Demarrage rapide (3 commandes)

```bash
git clone git@github.com:decarvalhoe/42-training.git && cd 42-training
./scripts/dev-up.sh
# Ouvrir http://localhost:3000
```

Le script `dev-up.sh` copie les `.env.example`, demarre tous les services via docker-compose, attend les healthchecks et affiche les URLs.

### Pre-requis

| Outil | Version minimale | Verification |
|-------|-----------------|--------------|
| Docker | 24+ avec compose plugin | `docker compose version` |
| Git | 2.x | `git --version` |

Pour le mode sans Docker (services individuels):

| Outil | Version minimale | Verification |
|-------|-----------------|--------------|
| Python | 3.13 | `python3 --version` |
| Node.js | 20 | `node --version` |
| npm | 9+ | `npm --version` |

### Services et ports

| Service | Port | Health endpoint | Description |
|---------|------|----------------|-------------|
| Web | 3000 | `http://localhost:3000` | Frontend Next.js |
| API | 8000 | `http://localhost:8000/health` | Backend FastAPI |
| AI Gateway | 8100 | `http://localhost:8100/health` | Assistance et gouvernance |
| PostgreSQL | 5432 | — | Base de donnees (user: `training`, pass: `training`) |
| Redis | 6379 | — | Cache |

### Arreter la stack

```bash
docker compose down
```

Pour supprimer aussi les volumes (reset complet des donnees):

```bash
docker compose down -v
```

### Mode sans Docker (services individuels)

Chaque service a un `.env.example` a copier en `.env`:

```bash
cp services/api/.env.example services/api/.env
cp services/ai_gateway/.env.example services/ai_gateway/.env
cp apps/web/.env.example apps/web/.env
```

Lancer chaque service dans un terminal separe:

```bash
# Terminal 1 — API
./scripts/start_api.sh

# Terminal 2 — AI Gateway
./scripts/start_ai_gateway.sh

# Terminal 3 — Web (npm install au premier lancement)
cd apps/web && npm install && cd ../..
./scripts/start_web.sh
```

Note: en mode sans Docker, PostgreSQL et Redis doivent etre demarres separement si l'API les requiert.

### Lancer les tests

```bash
# API
cd services/api && pip install -r requirements.txt && pytest tests -q

# AI Gateway
cd services/ai_gateway && pip install -r requirements.txt && pytest tests -q

# Web (build)
cd apps/web && npm ci && npm run build

# Smoke test (necessite API + AI Gateway en cours d'execution)
./scripts/smoke_mvp.sh
```

### Variables d'environnement

#### services/api/.env

| Variable | Defaut | Description |
|----------|--------|-------------|
| `API_PORT` | `8000` | Port du serveur API |
| `DATABASE_URL` | `postgresql+asyncpg://training:training@localhost:5432/training` | Connexion PostgreSQL |
| `REDIS_URL` | `redis://localhost:6379/0` | Connexion Redis |
| `APP_SECRET_KEY` | `change-me` | Cle secrete applicative |

#### services/ai_gateway/.env

| Variable | Defaut | Description |
|----------|--------|-------------|
| `AI_GATEWAY_PORT` | `8100` | Port du serveur AI Gateway |
| `AI_GATEWAY_API_BASE_URL` | `http://localhost:8000` | URL de l'API backend |
| `ANTHROPIC_API_KEY` | `change-me` | Cle API Anthropic (optionnel en dev) |
| `OPENAI_API_KEY` | `change-me` | Cle API OpenAI (optionnel en dev) |
| `EMBEDDING_PROVIDER` | `openai` | Provider d'embeddings |
| `VECTOR_STORE_URL` | `http://localhost:6333` | URL du vector store |

#### apps/web/.env

| Variable | Defaut | Description |
|----------|--------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | URL de l'API pour le frontend |
| `NEXT_PUBLIC_AI_GATEWAY_URL` | `http://localhost:8100` | URL de l'AI Gateway pour le frontend |
| `PORT` | `3000` | Port du serveur web |

### Depannage

#### Port deja utilise

```bash
# Trouver le processus qui occupe le port (ex: 8000)
lsof -i :8000
# ou
ss -tlnp | grep 8000

# Tuer le processus
kill -9 <PID>
```

#### Docker compose ne demarre pas

```bash
# Verifier que Docker tourne
docker info

# Verifier la config compose
docker compose config

# Voir les logs d'un service specifique
docker compose logs api
docker compose logs ai_gateway
docker compose logs web
```

#### Healthcheck en timeout

Le script `dev-up.sh` attend 120 secondes. Si le timeout est atteint:

```bash
# Voir l'etat des conteneurs
docker compose ps

# Verifier les logs du service en echec
docker compose logs --tail=50 <service>

# Reconstruire un service specifique
docker compose up -d --build <service>
```

#### Le frontend ne se connecte pas a l'API

- Verifier que l'API repond: `curl http://localhost:8000/health`
- Verifier `apps/web/.env`: `NEXT_PUBLIC_API_URL` doit pointer vers `http://localhost:8000`
- Le frontend a un fallback local et reste utilisable sans API

#### Reset complet

```bash
docker compose down -v
rm -f services/api/.env services/ai_gateway/.env apps/web/.env
./scripts/dev-up.sh
```

---

## EN

### Quick start (3 commands)

```bash
git clone git@github.com:decarvalhoe/42-training.git && cd 42-training
./scripts/dev-up.sh
# Open http://localhost:3000
```

The `dev-up.sh` script copies `.env.example` files, starts all services via docker-compose, waits for healthchecks and prints service URLs.

### Prerequisites

| Tool | Minimum version | Check |
|------|----------------|-------|
| Docker | 24+ with compose plugin | `docker compose version` |
| Git | 2.x | `git --version` |

For non-Docker mode (individual services):

| Tool | Minimum version | Check |
|------|----------------|-------|
| Python | 3.13 | `python3 --version` |
| Node.js | 20 | `node --version` |
| npm | 9+ | `npm --version` |

### Services and ports

| Service | Port | Health endpoint | Description |
|---------|------|----------------|-------------|
| Web | 3000 | `http://localhost:3000` | Next.js frontend |
| API | 8000 | `http://localhost:8000/health` | FastAPI backend |
| AI Gateway | 8100 | `http://localhost:8100/health` | Assistance and governance |
| PostgreSQL | 5432 | — | Database (user: `training`, pass: `training`) |
| Redis | 6379 | — | Cache |

### Stop the stack

```bash
docker compose down
```

To also remove volumes (full data reset):

```bash
docker compose down -v
```

### Non-Docker mode (individual services)

Each service has a `.env.example` to copy to `.env`:

```bash
cp services/api/.env.example services/api/.env
cp services/ai_gateway/.env.example services/ai_gateway/.env
cp apps/web/.env.example apps/web/.env
```

Start each service in a separate terminal:

```bash
# Terminal 1 — API
./scripts/start_api.sh

# Terminal 2 — AI Gateway
./scripts/start_ai_gateway.sh

# Terminal 3 — Web (npm install on first run)
cd apps/web && npm install && cd ../..
./scripts/start_web.sh
```

Note: in non-Docker mode, PostgreSQL and Redis must be started separately if the API requires them.

### Running tests

```bash
# API
cd services/api && pip install -r requirements.txt && pytest tests -q

# AI Gateway
cd services/ai_gateway && pip install -r requirements.txt && pytest tests -q

# Web (build)
cd apps/web && npm ci && npm run build

# Smoke test (requires API + AI Gateway running)
./scripts/smoke_mvp.sh
```

### Environment variables

#### services/api/.env

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PORT` | `8000` | API server port |
| `DATABASE_URL` | `postgresql+asyncpg://training:training@localhost:5432/training` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `APP_SECRET_KEY` | `change-me` | Application secret key |

#### services/ai_gateway/.env

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_GATEWAY_PORT` | `8100` | AI Gateway server port |
| `AI_GATEWAY_API_BASE_URL` | `http://localhost:8000` | Backend API URL |
| `ANTHROPIC_API_KEY` | `change-me` | Anthropic API key (optional in dev) |
| `OPENAI_API_KEY` | `change-me` | OpenAI API key (optional in dev) |
| `EMBEDDING_PROVIDER` | `openai` | Embedding provider |
| `VECTOR_STORE_URL` | `http://localhost:6333` | Vector store URL |

#### apps/web/.env

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API URL for frontend |
| `NEXT_PUBLIC_AI_GATEWAY_URL` | `http://localhost:8100` | AI Gateway URL for frontend |
| `PORT` | `3000` | Web server port |

### Troubleshooting

#### Port already in use

```bash
# Find the process using the port (e.g. 8000)
lsof -i :8000
# or
ss -tlnp | grep 8000

# Kill the process
kill -9 <PID>
```

#### Docker compose won't start

```bash
# Check Docker is running
docker info

# Validate compose config
docker compose config

# View logs for a specific service
docker compose logs api
docker compose logs ai_gateway
docker compose logs web
```

#### Healthcheck timeout

The `dev-up.sh` script waits 120 seconds. If the timeout is reached:

```bash
# Check container status
docker compose ps

# View logs of the failing service
docker compose logs --tail=50 <service>

# Rebuild a specific service
docker compose up -d --build <service>
```

#### Frontend can't connect to API

- Check API is responding: `curl http://localhost:8000/health`
- Check `apps/web/.env`: `NEXT_PUBLIC_API_URL` should point to `http://localhost:8000`
- The frontend has a local fallback and remains usable without the API

#### Full reset

```bash
docker compose down -v
rm -f services/api/.env services/ai_gateway/.env apps/web/.env
./scripts/dev-up.sh
```
