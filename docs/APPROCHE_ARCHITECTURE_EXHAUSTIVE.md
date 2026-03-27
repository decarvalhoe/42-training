# 42 Training - Approche et Architecture Exhaustive

## 1. Vision du produit

`42-training` n'est pas une simple collection de notes de preparation a 42.
Le produit vise a devenir un systeme d'apprentissage complet, progressif et
pilotable, concu pour preparer un profil senior a l'entree a 42 Lausanne puis a
l'evolution du tronc commun ancien et nouveau.

Le projet assume trois ambitions simultanees:

- reconstruire des fondamentaux pratiques apres des annees loin du code direct
- preparer de maniere realiste a la logique 42: autonomie, projets, defense,
  peer learning, evaluation par contrainte
- anticiper le nouveau paysage du cursus avec Python, IA, RAG et agents, sans
  affaiblir la colonne vertebrale shell + C + systeme

Le choix central est donc le suivant: une seule application, plusieurs pistes
pedagogiques, un seul noyau de progression et un seul moteur de gouvernance.

## 2. Probleme a resoudre

Le besoin utilisateur n'est pas celui d'un debutant absolu ni celui d'un etudiant
classique. Le profil cible est plus exigeant:

- personne experimentee en IT
- reprise du code bas niveau apres une longue interruption
- besoin de retrouver rapidement des reflexes de terminal, compilation,
  debogage et raisonnement algorithmique
- besoin d'un rythme libre
- besoin d'un outil qui consolide la discipline sans infantiliser

Le risque classique de ce type de profil est double:

- surconsommer des ressources trop abstraites ou trop theoriques
- compenser par l'IA et perdre la friction utile qui construit les reflexes 42

La reponse produit est donc une architecture qui encadre l'assistance et met la
comprehension avant la vitesse.

## 3. Positionnement par rapport a 42 Lausanne

Les sources officielles verifiees pour le produit confirment les axes suivants:

- pedagogie sans enseignants traditionnels
- apprentissage par projets
- peer learning
- progression flexible
- importance de C, Unix, algorithmes, systeme, reseau, web
- integration recente de l'IA dans le tronc commun a 42 Lausanne

Le produit n'essaie pas de reproduire une liste canonique complete des projets
internes de 42 Lausanne quand cette liste n'est pas publiquement detaillee.
Il distingue donc toujours:

- ce qui est officiel et certain
- ce qui est cartographie depuis des infographies ou la communaute
- ce qui est une interpretation pedagogique utile pour le produit

Cette separation est une decision de design et une decision d'integrite.

## 4. Decision structurante: une app, trois parcours

Le systeme suit une architecture triple, mais pas trois applications distinctes.

### 4.1 Parcours `shell`

Role:

- porte d'entree du systeme
- reconstruction rapide des reflexes Linux-first
- reduction de la peur du terminal
- base pratique pour la Piscine

Competences couvertes:

- navigation
- manipulation de fichiers
- redirections
- pipes
- permissions
- outils de recherche et lecture
- habitudes Linux quotidiennes

### 4.2 Parcours `c`

Role:

- noyau de rigueur 42
- preparation a `libft`, `printf`, `get_next_line`, `push_swap` et aux projets
  systeme

Competences couvertes:

- syntaxe et structures de controle
- fonctions et decomposition
- pointeurs et memoire
- build et warnings
- debug
- cas limites
- tests simples
- intuition algorithmique

### 4.3 Parcours `python_ai`

Role:

- anticipation du nouveau tronc commun
- introduction progressive a Python
- preparation a l'axe IA, RAG et agents

Competences couvertes:

- scripts Python simples
- structures de donnees
- POO legere
- automatisation
- retrieval
- usage discipline des LLM
- evaluation des reponses et politique de sources

## 5. Pourquoi cette architecture est coherente

L'architecture choisie n'est pas une juxtaposition arbitraire. Elle suit une
logique de dependances pedagogiques.

Ordre naturel:

1. shell pour reconstruire l'aisance
2. C pour reconstruire la rigueur
3. Python pour ouvrir la lane moderne
4. IA/RAG pour exploiter l'assistance sans trahir l'apprentissage

Ce choix evite deux erreurs:

- entrer trop tot dans l'IA avant les fondamentaux
- rester enferme dans une preparation purement historique alors que le cursus
  evolue

## 6. Architecture logique du systeme

Le produit est construit comme un monolithe modulaire inspire de RBOK.

### 6.1 Vue d'ensemble

- `apps/web`: interface utilisateur
- `services/api`: API applicative et systeme de record
- `services/ai_gateway`: moteur d'assistance, retrieval et garde-fous
- `packages/curriculum`: graphe pedagogique et cartographie des competences
- `packages/mentor-engine`: politiques de mentorat et contrats d'assistance
- `packages/shared-types`: schemas partages

### 6.2 Pourquoi un monolithe modulaire

Ce projet est encore au stade MVP. Un decoupage en microservices serait une
erreur d'architecture.

Le monolithe modulaire permet:

- une base coherent
- une faible friction de developpement
- une meilleure lisibilite des dependances pedagogiques
- une extraction future si une brique devient reellement autonome

Ce choix est directement inspire des bons aspects de RBOK.

## 7. Composants techniques crees

### 7.1 Frontend

Le frontend est un projet Next.js dans `apps/web`.

Responsabilites:

- afficher les trois parcours
- afficher les modules
- afficher l'etat de progression
- afficher la politique de sources
- servir de cockpit d'apprentissage

Le frontend a ete volontairement rendu resilient:

- il consomme l'API si elle est disponible
- il dispose d'un fallback local pour continuer a rendre la page si l'API n'est
  pas encore demarree

### 7.2 API applicative

L'API FastAPI dans `services/api` est le coeur du systeme.

Responsabilites:

- exposer les metadonnees du produit
- servir le dashboard complet
- servir la liste des tracks
- servir l'etat de progression
- accepter des mises a jour simples de progression

L'API est aujourd'hui encore alimentee par `progression.json`, mais son role est
clairement defini comme futur systeme de record applicatif.

### 7.3 AI Gateway

Le service `services/ai_gateway` isole la logique IA de la logique metier.

Responsabilites:

- exposer la politique de sources
- produire des reponses mentorales gardees
- empecher la derive vers la solution complete dans les phases fondamentales
- preparer l'arrivee d'un vrai RAG avec politique de sources stricte

Cette separation est essentielle. L'IA ne doit pas detenir la verite du produit.
Elle doit assister, filtrer, reformuler, guider, jamais gouverner seule.

## 8. Architecture agentique du produit

Le systeme cible ne se limite pas a un seul "assistant". Il prepare une
architecture agentique composee de roles complementaires.

### 8.1 Mentor

Mission:

- poser une bonne question
- donner un indice utile
- proposer une action suivante
- adapter la profondeur a la phase d'apprentissage

Interdits:

- donner la solution complete par defaut
- court-circuiter la friction utile

### 8.2 Librarian

Mission:

- retrouver la bonne ressource
- distinguer source officielle, doc communautaire, outil de test, metadata de
  solution
- justifier pourquoi une ressource est exploitable ou non

### 8.3 Reviewer

Mission:

- evaluer le travail produit
- relever les oublis de tests, de cas limites, de raisonnement
- se comporter comme un pair exigeant mais utile

### 8.4 Examiner

Mission:

- simuler une defense 42
- poser des questions de comprehension
- verifier la capacite a expliquer un choix ou un bug

### 8.5 Orchestrator

Mission:

- choisir quel agent appeler
- garantir la coherences des politiques
- arbitrer entre exploration, guidance, verification et defense

L'AI gateway est l'endroit naturel pour faire vivre cette future orchestration.

## 9. Modele de donnees pedagogique

La decision de produit la plus importante est de ne pas stocker le monde comme
une simple liste de projets.

Le modele logique cible comprend:

- `Track`
- `Module`
- `Skill`
- `Checkpoint`
- `ProjectMapping`
- `Resource`
- `Evidence`
- `MentorPolicy`
- `SourcePolicy`
- `LearnerProfile`
- `ProgressState`

### 9.1 Pourquoi un graphe de competences

Parce qu'un meme projet 42 mobilise plusieurs competences et qu'une meme
competence alimente plusieurs projets.

Exemple:

- `pipes` sert au shell, puis a la comprehension de `pipex`
- `malloc/free` sert a `libft`, `printf`, `gnl`, `minishell`
- `retrieval discipline` sert a la fois au RAG et a la methode d'apprentissage

Le graphe permet donc:

- des parcours non lineaires
- des checks plus intelligents
- une progression personnalisee

## 10. Politique de sources et RAG

C'est un axe majeur du systeme.

Le produit adopte une politique explicite par niveau de confiance et usage.

### 10.1 Tiers de sources

- `official_42`: verite de reference
- `community_docs`: explication et mapping
- `testers_and_tooling`: verification et validation
- `solution_metadata`: cartographie du parcours uniquement
- `blocked_solution_content`: bloque par defaut

### 10.2 Pourquoi cette politique est vitale

Sans cette politique, un systeme RAG sur 42 deriverait presque automatiquement
vers:

- fuite de solutions
- perte d'autonomie
- confusion entre comprendre et recopier

Le produit fait le choix inverse:

- exploiter la communaute pour se reperer
- exploiter les testers pour se verifier
- ne jamais transformer le repo en distributeur de corrections

## 11. DevOps inspire de RBOK

Les choix DevOps importes depuis RBOK sont selectifs.

### 11.1 Repris

- separation `web` / `api` / `ai_gateway`
- fichiers `.env.example`
- CI decoupee par service
- build conteneur par brique
- smoke tests simples
- scripts de demarrage courts

### 11.2 Rejetes

- hypothese Jelastic
- auth enterprise
- topologie prod multi-noeud prematuree
- complexite infra non justifiee

## 12. Verification deja realisee

Le MVP mis en place a ete verifie de maniere concrete.

Valide:

- tests `pytest` pour l'API
- tests `pytest` pour l'AI gateway
- build `next build` pour le frontend
- smoke HTTP complet: API 200, AI gateway 200, web 200

Limite connue:

- verification Playwright navigateur non poussee a cause d'un conflit de session
  Chrome locale existante, pas a cause du code de l'app

## 13. Etat du repository apres intervention

Le repo contient maintenant:

- la base shell-first historique
- une fondation applicative reelle
- une premiere cartographie 42 Lausanne / ancien-nouveau / triple parcours
- une CI minimale
- des scripts de demarrage
- une architecture documentaire qui peut servir a des humains et a des agents

## 14. Roadmap de construction conseillee

### Phase A - consolidation immediate

- documenter exhaustivement l'architecture
- fixer les conventions agents et GitHub
- stabiliser la lecture de `progression.json`

### Phase B - enrichissement pedagogique

- pages detail de module
- checklist de competences
- evidences de progression
- mode defense orale

### Phase C - persistance applicative

- base PostgreSQL
- modeles de progression et de ressources
- migration hors JSON pur

### Phase D - IA disciplinee

- vrai pipeline RAG
- indexation des ressources autorisees
- filtres de reponse par phase pedagogique
- journaux d'explications et d'usages

### Phase E - experience 42-like

- peer review simulee
- oral defense
- checkpoints chronometres
- entrainement par contrainte

## 15. Principes non negociables

- Linux-first
- autonomie d'apprentissage
- pas de solution complete par defaut
- separation stricte entre source officielle et interpretation communautaire
- architecture simple avant architecture spectaculaire
- l'IA assiste la maitrise, elle ne remplace pas la comprehension

## 16. Conclusion

L'architecture construite est volontairement pragmatique.

Elle ne cherche ni a rejouer RBOK tel quel, ni a reproduire une plateforme de
cours classique, ni a singer 42 de maniere superficielle. Elle cree un systeme
coherent pour un besoin precis:

- reprendre le code serieusement
- se preparer a 42 Lausanne de maniere moderne
- integrer Python et l'axe IA sans trahir les fondamentaux
- construire un outil durable, extensible et gouvernable

C'est une bonne base produit. La suite doit maintenant porter sur la profondeur
pedagogique, pas sur une inflation technique prematuree.
