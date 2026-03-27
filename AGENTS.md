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
