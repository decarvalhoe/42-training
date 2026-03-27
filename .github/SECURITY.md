# Security Policy

## FR

### Signaler une vulnerabilite

Si tu decouvres un probleme de securite, ne publie pas les details d'exploitation dans une issue publique.

Remonte-le de maniere privee aux maintainers avec:

- le composant affecte
- les etapes de reproduction
- l'impact estime
- une remediation suggeree si tu en as une

En attendant une adresse securite dediee, utiliser un canal prive maintainer.

### Perimetre

Les concerns securite incluent:

- fuite de secrets
- vulnerabilites de dependances
- chemins d'injection de prompt non maitrises dans l'AI gateway
- recuperation de contenu solution qui devrait etre bloque
- exposition de donnees apprenant ou d'etat de session futur
- execution dangereuse dans les features liees au shell

### Priorites actuelles

- garder `.env` et les secrets hors de git
- garder l'AI gateway separee de la verite produit
- contraindre les futurs chemins d'execution d'outils
- garder les dependances a jour, surtout le stack web
- empecher le retrieval libre depuis des repos de solutions

### Regles dures

- ne jamais commit de secret
- ne jamais injecter de token dans une URL de remote
- ne jamais contourner la politique de sources dans la couche assistant
- ne jamais exposer donnees apprenant ou credentials futurs sans necessite

### Dependances

Le stack web doit rester sur une version corrigee de Next.js.
Si une alerte dependance apparait, il faut la traiter avant d'elargir l'exposition du service.

## EN

### Reporting a vulnerability

If you discover a security issue, do not publish exploit details in a public issue.

Report it privately to the maintainers with:

- affected component
- reproduction steps
- estimated impact
- suggested remediation if known

Until a dedicated security mailbox exists, use a private maintainer channel.

### Scope

Security concerns include:

- secret leakage
- dependency vulnerabilities
- unsafe prompt-injection paths in the AI gateway
- retrieval of solution content that should be blocked
- exposure of learner data or future session state
- unsafe execution flows in shell-related features

### Current priorities

- keep `.env` files and secrets out of git
- keep the AI gateway separated from product truth
- constrain future tool-execution paths
- keep dependencies updated, especially the web stack
- prevent unrestricted retrieval from solution repositories

### Hard rules

- never commit secrets
- never embed tokens in repository URLs
- never bypass source policy in the assistant layer
- never expose learner data or future credentials without necessity

### Dependencies

The web stack should stay on a patched Next.js release.
If a dependency warning appears, address it before expanding service exposure.
