# Contributing to 42 Training

## FR

### Objectif

Ce projet construit une plateforme disciplinee de preparation a 42 Lausanne.
Il est a la fois:

- un espace personnel Linux-first d'apprentissage
- une application en evolution avec `web`, `api` et `ai_gateway`

Les contributions doivent preserver les deux dimensions.

### Principes de contribution

- garder le produit aligne avec la philosophie 42
- privilegier des pull requests petites et coherentes
- documenter les changements d'architecture
- ne pas affaiblir la politique de sources
- ne pas transformer le projet en depot de solutions

### Branching

Flux recommande:

- creer une branche de feature
- ouvrir une pull request vers la branche d'integration active
- garder des commits cibles et descriptifs

Styles de commits encourages:

- `feat:`
- `fix:`
- `docs:`
- `refactor:`
- `test:`
- `chore:`

### Avant d'ouvrir une PR

Si tu touches l'API:

```bash
cd services/api
pytest tests -q
```

Si tu touches l'AI gateway:

```bash
cd services/ai_gateway
pytest tests -q
```

Si tu touches le frontend:

```bash
cd apps/web
npm install
npm run build
```

Si tu touches le comportement transverse de l'app:

```bash
./scripts/smoke_mvp.sh
```

### Exigences documentaires

Si tu modifies l'architecture, la direction produit ou la gouvernance des sources, mets a jour les documents pertinents:

- `README.md`
- `docs/APPROCHE_ARCHITECTURE_EXHAUSTIVE.md`
- `ARCHITECTURE_TARGET.md`
- `docs/DEVOPS_RBOK_ADAPTATION.md`
- `docs/adr/`
- `AGENTS.md`
- `CLAUDE.md`

### Gouvernance des sources

Les contributeurs doivent respecter ceci:

- les sources officielles 42 sont la base de verite
- la documentation communautaire sert a expliquer et cartographier
- les testers servent a verifier
- les repos de solutions servent aux metadonnees par defaut
- la generation directe de reponses depuis des dumps de solutions n'est pas acceptable pour les phases fondamentales

### Contenu attendu dans une PR

Une bonne PR doit expliquer:

- ce qui a change
- pourquoi c'est necessaire
- comment cela a ete verifie
- ce qui reste volontairement hors scope

### Criteres de review

Les changements sont evalues sur:

- coherence pedagogique
- clarte d'architecture
- discipline de gouvernance des sources
- qualite de verification
- maintenabilite

## EN

### Purpose

This project builds a disciplined preparation platform for 42 Lausanne.
It is both:

- a Linux-first personal learning workspace
- an evolving application with `web`, `api` and `ai_gateway`

Contributions must preserve both dimensions.

### Contribution principles

- keep the product aligned with the 42 philosophy
- prefer small, coherent pull requests
- document architecture changes
- do not weaken the source policy
- do not turn the project into a solution dump

### Branching

Recommended flow:

- create a feature branch
- open a pull request against the active integration branch
- keep commits focused and descriptive

Encouraged commit styles:

- `feat:`
- `fix:`
- `docs:`
- `refactor:`
- `test:`
- `chore:`

### Before opening a PR

If you touched the API:

```bash
cd services/api
pytest tests -q
```

If you touched the AI gateway:

```bash
cd services/ai_gateway
pytest tests -q
```

If you touched the web app:

```bash
cd apps/web
npm install
npm run build
```

If you touched shared app behavior:

```bash
./scripts/smoke_mvp.sh
```

### Documentation expectations

If you change architecture, product direction or source governance, update the relevant documents:

- `README.md`
- `docs/APPROCHE_ARCHITECTURE_EXHAUSTIVE.md`
- `ARCHITECTURE_TARGET.md`
- `docs/DEVOPS_RBOK_ADAPTATION.md`
- `docs/adr/`
- `AGENTS.md`
- `CLAUDE.md`

### Source governance

Contributors must respect the following:

- official 42 sources are the truth baseline
- community docs help explain and map
- testers help verify
- solution repositories are metadata sources by default
- direct answer generation from solution dumps is not acceptable for foundation phases

### Pull request content

A good PR should explain:

- what changed
- why it is needed
- how it was verified
- what remains intentionally out of scope

### Review criteria

Changes are evaluated on:

- pedagogical coherence
- architecture clarity
- source-governance discipline
- verification quality
- maintainability
