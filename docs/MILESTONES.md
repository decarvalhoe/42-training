# Milestones

## Vue d'ensemble / Overview

Le backlog est organise en trois milestones progressifs.
Chaque issue porte un label `priority:` et un label `area:` qui determinent son placement.

The backlog is organized into three progressive milestones.
Each issue carries a `priority:` and `area:` label that determine its placement.

**Regle de tri / Sorting rule:** `priority:high` → MVP, `priority:medium` → MVP ou v1 selon la dependance, `priority:low` → v1 ou v2.

---

## MVP — Fondations utilisables

**Objectif:** Un parcours navigable avec curriculum structure, API typee, frontend fonctionnel, mentor LLM branche et CI de base.

| # | Titre | Area | Priorite |
|---|-------|------|----------|
| 10 | Definir les entites Skill, Checkpoint, Resource, Evidence dans le schema curriculum | curriculum | high |
| 11 | Ajouter les prerequis entre modules dans le curriculum JSON | curriculum | high |
| 12 | Enrichir chaque module avec objectifs, criteres de sortie et resources | curriculum | medium |
| 13 | Documenter le niveau de confiance par source | curriculum | medium |
| 15 | Ajouter le routing Next.js: /tracks/[id], /modules/[id], /progression | frontend | high |
| 16 | Creer la page detail track avec liste de modules et etat progression | frontend | high |
| 17 | Creer la page detail module avec skills, prerequis, deliverable | frontend | high |
| 18 | Creer la vue progression personnelle (checklist, backlog, prochaine action) | frontend | high |
| 19 | Creer le composant source-policy badge (visuel de confiance par source) | frontend | medium |
| 20 | Ajouter navigation header/sidebar entre les vues | frontend | medium |
| 22 | Introduire le schema Pydantic LearnerProfile et ProgressState | backend | high |
| 23 | Remplacer dict[str, object] par des schemas types sur tous les endpoints | backend | high |
| 24 | Ajouter les endpoints CRUD pour modules progression (start, complete, skip) | backend | high |
| 25 | Separer les endpoints lecture curriculum vs mutations progression | backend | medium |
| 27 | Augmenter la couverture de tests API (happy path + edge cases + validation) | backend | high |
| 29 | Brancher un vrai appel LLM (Claude API) dans le mentor respond | ai | high |
| 30 | Creer la couche retrieval abstraite avec interface SourceProvider | ai | high |
| 34 | Tests de non-regression sur les garde-fous (pas de solution directe en foundation) | ai | high |
| 40 | Ajouter ruff lint + mypy typecheck dans la CI pour Python | devops | high |
| 41 | Ajouter ESLint + TypeScript strict dans la CI pour le web | devops | high |
| 42 | Rendre docker-compose dev reellement executable (.env auto) | devops | high |
| 43 | Ajouter healthcheck docker sur chaque service | devops | medium |
| 45 | Documenter le runbook local (setup en 3 commandes) | devops | medium |
| 46 | Creer les milestones MVP / v1 / v2 sur GitHub | product | high |
| 47 | Definir la convention de branches et PR pour multi-agents | product | high |
| 48 | Documenter les ownerships par area dans AGENTS.md | product | medium |

**Total: 26 issues** (17 high, 9 medium)

---

## v1 — Profondeur et evaluation

**Objectif:** Persistence PostgreSQL, roles IA supplementaires (Librarian, Reviewer), validation metier, rubrics, CI smoke tests.

| # | Titre | Area | Priorite |
|---|-------|------|----------|
| 14 | Creer le mapping ancien parcours 42 vers nouveau curriculum interprete | curriculum | low |
| 21 | Responsive mobile-first pour les vues principales | frontend | low |
| 26 | Ajouter validation metier (prerequis, phases ordonnees) | backend | medium |
| 28 | Preparer l abstraction repository pour le futur switch JSON vers PostgreSQL | backend | medium |
| 31 | Implementer le role Librarian (recherche de ressources filtrees par policy) | ai | medium |
| 32 | Implementer le role Reviewer (critique de code peer-style) | ai | medium |
| 33 | Ajouter la journalisation provenance dans chaque reponse mentor | ai | medium |
| 35 | Definir les rubrics de validation par track (shell, C, Python) | curriculum | medium |
| 36 | Modeliser Checkpoint, Review, DefenseSession dans les schemas API | backend | medium |
| 37 | Creer l endpoint de soumission checkpoint (evidence + auto-evaluation) | backend | medium |
| 39 | Ajouter les checklists de sortie de module dans le curriculum | curriculum | medium |
| 44 | Ajouter un smoke test CI qui lance compose + verifie les health endpoints | devops | medium |
| 49 | Modeliser les tables coeur (learner_profile, progression, evidence, review) | backend | medium |
| 50 | Choisir et configurer SQLAlchemy/SQLModel + Alembic | backend | medium |
| 51 | Concevoir le chemin d import JSON vers PostgreSQL (migration initiale) | backend | low |

**Total: 15 issues** (0 high, 11 medium, 4 low)

---

## v2 — Autonomie et metriques

**Objectif:** Defense orale, metriques produit/pedagogiques, fonctionnalites avancees d'agent.

| # | Titre | Area | Priorite |
|---|-------|------|----------|
| 38 | Concevoir le flow defense orale MVP (questions, reponses, scoring) | ai | low |
| 52 | Definir les premieres metriques produit et pedagogiques | product | low |

**Total: 2 issues** (0 high, 0 medium, 2 low)

---

## EPICs (hors milestones)

Les EPICs sont des issues-parapluie qui regroupent des issues enfants reparties dans les milestones ci-dessus. Elles ne portent pas de milestone elles-memes.

| # | Titre | Areas |
|---|-------|-------|
| 2 | EPIC: Structurer le curriculum et le graphe pedagogique | product, curriculum |
| 3 | EPIC: Construire le dashboard et l information architecture apprenant | frontend, product |
| 4 | EPIC: Faire de l API le vrai moteur de progression et de persistance | backend, product |
| 5 | EPIC: Construire l AI gateway, le mentor et la politique RAG | ai, backend |
| 6 | EPIC: Mettre en place le moteur d evaluation, review et defense | product, curriculum |
| 7 | EPIC: Renforcer DevOps, CI, environnements et qualite | frontend, backend, devops |
| 8 | EPIC: Organiser la gouvernance produit, backlog et multi-agents | product |
| 9 | EPIC: Planifier la migration PostgreSQL et les analytics pedagogiques | backend, product |
