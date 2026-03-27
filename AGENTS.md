# AGENTS.md

## FR

Instructions globales pour les agents qui travaillent sur `42-training`.

### Mission

Construire une plateforme d'apprentissage disciplinee pour preparer 42 Lausanne.

Le depot sert deux couches simultanement:

- l'espace historique de preparation shell-first
- la nouvelle application MVP avec `web`, `api` et `ai_gateway`

Les agents doivent preserver les deux.

### Intention produit

Ce projet n'est pas une app edtech generique.

C'est un systeme de preparation guide, auto-rythme, centre sur:

- shell
- C
- Python + IA

Le produit doit rester compatible avec la philosophie 42:

- autonomie d'abord
- apprentissage par projets
- raisonnement type pair-review
- pas de solution complete par defaut
- distinction forte entre faits officiels et interpretation communautaire

### Regles d'architecture

- Conserver une logique de monolithe modulaire.
- `services/api` est le systeme de record applicatif.
- `services/ai_gateway` est une couche d'assistance et de gouvernance, pas la source de verite.
- `apps/web` consomme le backend et presente le systeme d'apprentissage.
- Les definitions pedagogiques partagees vivent dans `packages/`.
- Ne pas introduire de microservices sans besoin concret de scalabilite ou d'autonomie forte.

### Regles de gouvernance des sources

Pour tout travail sur retrieval, prompts, assistance ou documentation:

- les sources officielles 42 servent de verite de reference
- la documentation communautaire sert a expliquer et cartographier
- les testers et outils servent a verifier
- les repos de solutions servent a la cartographie et aux metadonnees uniquement
- le contenu de solution directe est bloque par defaut en phase fondamentale

Ne pas affaiblir cette politique sans raison explicite.

### Agents actifs

Cinq agents CLI travaillent en parallele sur ce depot:

| Agent | Area principale | Exemples |
|-------|-----------------|----------|
| `claude` | curriculum, product, architecture | schemas curriculum, milestones, conventions |
| `codex` | backend | API endpoints, schemas Pydantic, tests |
| `copilot` | frontend | pages Next.js, composants, navigation |
| `cursor` | ai | AI gateway, mentor, retrieval, garde-fous |
| `gemini` | devops | CI, Docker, linting, healthchecks |

Chaque agent travaille sur une issue a la fois, assignee via `gh issue list --assignee`.

### Ownerships par area

Chaque agent est proprietaire d'une ou deux areas. Le proprietaire a autorite sur les fichiers de son area et est responsable de la qualite, des tests et de la coherence dans son perimetre.

#### claude — curriculum + product

- **Labels issues:** `area:curriculum`, `area:product`
- **Repertoires:**
  - `packages/curriculum/` — schemas, donnees, scripts de validation
  - `docs/` — documentation architecture, ADR, milestones
  - `AGENTS.md`, `CLAUDE.md`, `ARCHITECTURE_TARGET.md`, `README.md`
- **Responsabilites:**
  - Structurer et enrichir le curriculum JSON
  - Maintenir la politique de sources et les niveaux de confiance
  - Documenter l'architecture, les conventions et la gouvernance
  - Proteger la philosophie d'apprentissage dans tout le depot
  - Arbitrer les decisions transverses entre areas

#### codex — backend

- **Labels issues:** `area:backend`
- **Repertoires:**
  - `services/api/` — endpoints, schemas Pydantic, logique metier
- **Responsabilites:**
  - Definir et implementer les endpoints API REST
  - Creer les schemas types (Pydantic) pour les contrats de donnees
  - Ecrire et maintenir les tests API (`pytest`)
  - Preparer la couche d'abstraction pour la migration PostgreSQL
  - Garantir que l'API reste le systeme de record applicatif

#### copilot — frontend

- **Labels issues:** `area:frontend`
- **Repertoires:**
  - `apps/web/` — pages Next.js, composants, navigation, styles
- **Responsabilites:**
  - Construire les pages et composants de l'interface apprenant
  - Implementer le routing et la navigation
  - Consommer l'API backend et afficher les donnees curriculum
  - Respecter l'accessibilite et le responsive
  - Ne pas introduire de logique metier dans le frontend

#### cursor — ai

- **Labels issues:** `area:ai`
- **Repertoires:**
  - `services/ai_gateway/` — mentor, retrieval, roles IA, garde-fous
  - `packages/mentor-engine/` — moteur de prompts (quand actif)
  - `prompts/` — templates de prompts
- **Responsabilites:**
  - Implementer les roles IA (Mentor, Librarian, Reviewer)
  - Construire la couche retrieval et la politique de sources
  - Maintenir les garde-fous (pas de solution directe en phase fondamentale)
  - Brancher et configurer les appels LLM
  - Ecrire les tests de non-regression sur les garde-fous

#### gemini — devops

- **Labels issues:** `area:devops`
- **Repertoires:**
  - `docker-compose.yml`, `scripts/` — orchestration et automatisation
  - `.github/workflows/` — CI/CD pipelines
  - `services/*/Dockerfile` — images Docker par service
- **Responsabilites:**
  - Maintenir l'environnement de developpement local (Docker, scripts)
  - Configurer et faire evoluer la CI (linting, tests, build)
  - Ajouter les healthchecks et smoke tests
  - Documenter le runbook local (setup en 3 commandes)

#### Matrice de responsabilite

| Ressource | claude | codex | copilot | cursor | gemini |
|-----------|--------|-------|---------|--------|--------|
| `packages/curriculum/` | **owner** | | | | |
| `docs/`, `AGENTS.md`, `CLAUDE.md` | **owner** | | | | |
| `services/api/` | | **owner** | | | |
| `apps/web/` | | | **owner** | | |
| `services/ai_gateway/` | | | | **owner** | |
| `packages/mentor-engine/`, `prompts/` | | | | **owner** | |
| `docker-compose.yml`, `scripts/` | | | | | **owner** |
| `.github/workflows/` | | | | | **owner** |
| `README.md` | **owner** | contrib | contrib | contrib | contrib |
| `packages/shared-types/` | coord | contrib | contrib | contrib | |

**owner** = autorite sur le fichier, responsable review. **contrib** = peut modifier via PR avec review du owner. **coord** = coordonne les changements transverses.

### Convention de branches et PR

#### Nommage des branches

```
feat/<agent>/<issue>-<description-courte>
fix/<agent>/<issue>-<description-courte>
docs/<agent>/<issue>-<description-courte>
```

Exemples reels:

```
feat/claude/13-source-confidence-levels
feat/codex/24-module-progression-crud
feat/copilot/17-module-detail-page
feat/cursor/30-retrieval-source-provider
feat/gemini/42-docker-compose-dev
```

#### Workflow complet

1. **Prendre une issue** — verifier qu'elle est assignee et pas deja en cours par un autre agent.
2. **Creer la branche** — toujours depuis `develop` a jour:
   ```bash
   git checkout develop && git pull
   git checkout -b feat/<agent>/<issue>-<slug>
   ```
3. **Commiter** — style conventional commits:
   - `feat:` nouvelle fonctionnalite
   - `fix:` correction de bug
   - `docs:` documentation uniquement
   - `refactor:` restructuration sans changement de comportement
   - `test:` ajout ou correction de tests
   - `chore:` maintenance, config, outillage
   - Inclure `(#<issue>)` dans le message pour la tracabilite.
4. **Tester avant push** — lancer les tests pertinents pour l'area modifiee.
5. **Pousser et creer la PR:**
   ```bash
   git push -u origin feat/<agent>/<issue>-<slug>
   gh pr create --base develop --title '<type>: <description> (#<issue>)' --body 'Closes #<issue>. ...'
   ```
6. **Review** — un autre agent ou le mainteneur review. Ne pas merger soi-meme sans review.

#### Cible PR

Toutes les PR ciblent `develop`. Jamais `main` directement.

`main` est mis a jour uniquement par merge de `develop` apres validation.

#### Resolution de conflits entre agents

Quand deux agents modifient le meme fichier:

1. **Prevention** — les areas sont reparties par agent. Les fichiers partages (`42_lausanne_curriculum.json`, `AGENTS.md`) sont reserves a `claude` par defaut.
2. **Detection** — avant de push, faire `git fetch && git rebase origin/develop`. Si conflit, le resoudre localement.
3. **Priorite** — si deux PR touchent le meme fichier:
   - la PR la plus avancee (deja approuvee) passe en premier
   - l'autre agent rebase apres merge
   - en cas d'egalite, l'agent dont l'area est proprietaire du fichier a priorite
4. **Fichiers partages** — les fichiers listes dans "Zones sensibles" ne doivent etre modifies que par l'agent responsable de l'area, sauf coordination explicite.
5. **Escalade** — si un conflit ne peut pas etre resolu mecaniquement, le signaler dans la PR et attendre une decision du mainteneur.

### Zones sensibles du repo

- `packages/curriculum/data/42_lausanne_curriculum.json`
- `progression.json`
- `services/api/app/main.py`
- `services/ai_gateway/app/main.py`
- `apps/web/app/page.tsx`

### Style de travail

- Faire des changements petits et coherents.
- Garder la documentation alignee avec le code.
- Preserver les workflows Linux-first de `scripts/`.
- Eviter les abstractions speculatives.
- Garder l'application utilisable avant la base de donnees complete.
- Ne jamais transformer le produit en generateur de solutions.

### Commandes utiles

API:

```bash
cd services/api
pytest tests -q
uvicorn app.main:app --reload --port 8000
```

AI gateway:

```bash
cd services/ai_gateway
pytest tests -q
uvicorn app.main:app --reload --port 8100
```

Web:

```bash
cd apps/web
npm install
npm run build
npm run dev
```

Smoke:

```bash
./scripts/smoke_mvp.sh
```

### Devoir documentaire

Si l'architecture change, mettre a jour au minimum:

- `README.md`
- `docs/APPROCHE_ARCHITECTURE_EXHAUSTIVE.md`
- `ARCHITECTURE_TARGET.md`
- `docs/DEVOPS_RBOK_ADAPTATION.md`
- `docs/adr/`

### Garde-fous

- Ne pas ajouter de dump de solutions.
- Ne pas traiter les noms non officiels du cursus comme verite canonique.
- Ne pas effacer le workflow historique shell-first.
- Ne pas suradapter le produit a une idee UI temporaire.

## EN

Repository-wide instructions for agents working on `42-training`.

### Mission

Build a disciplined learning platform for 42 Lausanne preparation.

The repository serves two layers at once:

- the historical shell-first mentor workspace
- the new MVP application with `web`, `api` and `ai_gateway`

Agents must preserve both.

### Product intent

This is not a generic edtech app.

It is a guided, self-paced preparation system centered on:

- shell
- C
- Python + AI

The product must remain compatible with the 42 philosophy:

- autonomy first
- project-based learning
- peer-style reasoning
- no full solution by default
- a strong distinction between official facts and community interpretation

### Architectural rules

- Keep a modular monolith approach.
- `services/api` is the application system of record.
- `services/ai_gateway` is an assistance and governance layer, not the truth source.
- `apps/web` consumes the backend and presents the learning system.
- Shared learning definitions belong under `packages/`.
- Do not introduce microservices without a concrete reason.

### Source-governance rules

For work involving retrieval, prompts, assistance flows or documentation:

- official 42 sources are the ground-truth baseline
- community documentation supports explanation and mapping
- testers and tools support verification
- solution repositories are metadata and mapping sources only
- direct solution content is blocked by default in foundation phases

Do not weaken this policy casually.

### Active agents

Five CLI agents work in parallel on this repository:

| Agent | Primary area | Examples |
|-------|-------------|----------|
| `claude` | curriculum, product, architecture | curriculum schemas, milestones, conventions |
| `codex` | backend | API endpoints, Pydantic schemas, tests |
| `copilot` | frontend | Next.js pages, components, navigation |
| `cursor` | ai | AI gateway, mentor, retrieval, guardrails |
| `gemini` | devops | CI, Docker, linting, healthchecks |

Each agent works on one issue at a time, assigned via `gh issue list --assignee`.

### Ownerships by area

Each agent owns one or two areas. The owner has authority over files in their area and is responsible for quality, tests and consistency within their scope.

#### claude — curriculum + product

- **Issue labels:** `area:curriculum`, `area:product`
- **Directories:**
  - `packages/curriculum/` — schemas, data, validation scripts
  - `docs/` — architecture docs, ADRs, milestones
  - `AGENTS.md`, `CLAUDE.md`, `ARCHITECTURE_TARGET.md`, `README.md`
- **Responsibilities:**
  - Structure and enrich the curriculum JSON
  - Maintain source policy and confidence levels
  - Document architecture, conventions and governance
  - Protect the learning philosophy across the repository
  - Arbitrate cross-area decisions

#### codex — backend

- **Issue labels:** `area:backend`
- **Directories:**
  - `services/api/` — endpoints, Pydantic schemas, business logic
- **Responsibilities:**
  - Define and implement REST API endpoints
  - Create typed schemas (Pydantic) for data contracts
  - Write and maintain API tests (`pytest`)
  - Prepare the repository abstraction for PostgreSQL migration
  - Ensure the API remains the application system of record

#### copilot — frontend

- **Issue labels:** `area:frontend`
- **Directories:**
  - `apps/web/` — Next.js pages, components, navigation, styles
- **Responsibilities:**
  - Build learner-facing pages and components
  - Implement routing and navigation
  - Consume the backend API and display curriculum data
  - Respect accessibility and responsive design
  - Do not introduce business logic in the frontend

#### cursor — ai

- **Issue labels:** `area:ai`
- **Directories:**
  - `services/ai_gateway/` — mentor, retrieval, AI roles, guardrails
  - `packages/mentor-engine/` — prompt engine (when active)
  - `prompts/` — prompt templates
- **Responsibilities:**
  - Implement AI roles (Mentor, Librarian, Reviewer)
  - Build the retrieval layer and source policy enforcement
  - Maintain guardrails (no direct solutions in foundation phases)
  - Wire and configure LLM calls
  - Write regression tests for guardrails

#### gemini — devops

- **Issue labels:** `area:devops`
- **Directories:**
  - `docker-compose.yml`, `scripts/` — orchestration and automation
  - `.github/workflows/` — CI/CD pipelines
  - `services/*/Dockerfile` — Docker images per service
- **Responsibilities:**
  - Maintain the local development environment (Docker, scripts)
  - Configure and evolve CI (linting, tests, build)
  - Add healthchecks and smoke tests
  - Document the local runbook (setup in 3 commands)

#### Responsibility matrix

| Resource | claude | codex | copilot | cursor | gemini |
|----------|--------|-------|---------|--------|--------|
| `packages/curriculum/` | **owner** | | | | |
| `docs/`, `AGENTS.md`, `CLAUDE.md` | **owner** | | | | |
| `services/api/` | | **owner** | | | |
| `apps/web/` | | | **owner** | | |
| `services/ai_gateway/` | | | | **owner** | |
| `packages/mentor-engine/`, `prompts/` | | | | **owner** | |
| `docker-compose.yml`, `scripts/` | | | | | **owner** |
| `.github/workflows/` | | | | | **owner** |
| `README.md` | **owner** | contrib | contrib | contrib | contrib |
| `packages/shared-types/` | coord | contrib | contrib | contrib | |

**owner** = authority over the file, responsible for review. **contrib** = may modify via PR with owner review. **coord** = coordinates cross-area changes.

### Branch and PR convention

#### Branch naming

```
feat/<agent>/<issue>-<short-description>
fix/<agent>/<issue>-<short-description>
docs/<agent>/<issue>-<short-description>
```

Real examples:

```
feat/claude/13-source-confidence-levels
feat/codex/24-module-progression-crud
feat/copilot/17-module-detail-page
feat/cursor/30-retrieval-source-provider
feat/gemini/42-docker-compose-dev
```

#### Full workflow

1. **Pick an issue** — verify it is assigned and not already in progress by another agent.
2. **Create the branch** — always from up-to-date `develop`:
   ```bash
   git checkout develop && git pull
   git checkout -b feat/<agent>/<issue>-<slug>
   ```
3. **Commit** — use conventional commits:
   - `feat:` new feature
   - `fix:` bug fix
   - `docs:` documentation only
   - `refactor:` restructuring without behavior change
   - `test:` adding or fixing tests
   - `chore:` maintenance, config, tooling
   - Include `(#<issue>)` in the message for traceability.
4. **Test before push** — run the relevant tests for the area you modified.
5. **Push and create the PR:**
   ```bash
   git push -u origin feat/<agent>/<issue>-<slug>
   gh pr create --base develop --title '<type>: <description> (#<issue>)' --body 'Closes #<issue>. ...'
   ```
6. **Review** — another agent or the maintainer reviews. Do not self-merge without review.

#### PR target

All PRs target `develop`. Never `main` directly.

`main` is updated only by merging `develop` after validation.

#### Conflict resolution between agents

When two agents modify the same file:

1. **Prevention** — areas are split by agent. Shared files (`42_lausanne_curriculum.json`, `AGENTS.md`) default to `claude`.
2. **Detection** — before pushing, run `git fetch && git rebase origin/develop`. If conflicts arise, resolve them locally.
3. **Priority** — if two PRs touch the same file:
   - the more advanced PR (already approved) merges first
   - the other agent rebases after merge
   - if tied, the agent whose area owns the file has priority
4. **Shared files** — files listed under "Current repo hotspots" should only be modified by the area-owning agent unless explicitly coordinated.
5. **Escalation** — if a conflict cannot be resolved mechanically, flag it in the PR and wait for a maintainer decision.

### Current repo hotspots

- `packages/curriculum/data/42_lausanne_curriculum.json`
- `progression.json`
- `services/api/app/main.py`
- `services/ai_gateway/app/main.py`
- `apps/web/app/page.tsx`

### Working style

- Prefer small, coherent changes.
- Keep docs aligned with code.
- Preserve Linux-first workflows in `scripts/`.
- Avoid speculative abstractions.
- Keep the app usable before the full database layer exists.
- Do not turn the product into a solution generator.

### Useful commands

API:

```bash
cd services/api
pytest tests -q
uvicorn app.main:app --reload --port 8000
```

AI gateway:

```bash
cd services/ai_gateway
pytest tests -q
uvicorn app.main:app --reload --port 8100
```

Web:

```bash
cd apps/web
npm install
npm run build
npm run dev
```

Smoke:

```bash
./scripts/smoke_mvp.sh
```

### Documentation duties

If architecture changes, update at least:

- `README.md`
- `docs/APPROCHE_ARCHITECTURE_EXHAUSTIVE.md`
- `ARCHITECTURE_TARGET.md`
- `docs/DEVOPS_RBOK_ADAPTATION.md`
- `docs/adr/`

### Guardrails

- Do not add solution dumps.
- Do not treat unofficial curriculum names as canonical truth.
- Do not erase the shell-first workflow.
- Do not overfit the product to a temporary UI idea.
