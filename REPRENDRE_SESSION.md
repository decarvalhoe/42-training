# Reprendre une session 42

## Regle simple

Ne reprends jamais la session a partir d'une etape ecrite a la main dans ce
fichier. La source de verite est [`progression.json`](progression.json).

## Reprise standard

```bash
cd ~/42-training
./scripts/doctor.sh
./scripts/print_session_state.sh
cat progression.json | python3 -m json.tool
```

Si tu veux travailler avec le mentor Linux:

```bash
./scripts/start_42_mentor_env.sh .
tmux attach -t learn42
```

## Rappel pedagogique

- apprendre d'abord
- demander une piste, pas la solution
- tester souvent
- compiler souvent
- documenter les erreurs utiles avec `./scripts/update_progress.sh`

## Contexte court pour Claude

Copie ce bloc si tu veux reprendre une session mentor:

```text
Je prepare la Piscine 42 Lausanne.
Je travaille uniquement depuis Linux ou WSL Ubuntu.
Le repo courant est ~/42-training.
Lis d'abord progression.json et suis la progression courante.
Agis comme un mentor pedagogique: observation, une question, un indice,
une action suivante. Pas de solution complete par defaut.
```
