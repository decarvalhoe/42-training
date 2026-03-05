# 🎯 42-training - Préparation Piscine 42 Lausanne

> **Objectif:** Réapprendre les bases depuis ZÉRO pour la Piscine 42 Lausanne (Juin 2026)

## 📊 Contexte

Après des années dans des rôles de leadership technique (Chef de Projet, Ingénieur CSV Pharma, Tech Lead, Solution Architect, Business Analyst, IT Manufacturing), je n'ai plus codé directement. J'ai géré des équipes, conçu des architectures, validé des systèmes critiques, mais le code "hands-on" est devenu distant.

Aujourd'hui, j'utilise des agents IA (Claude, Copilot, Cursor, etc.) pour créer des applications professionnelles complexes, gérer de l'infrastructure via CLI, faire des audits automatisés (projet RBOK et autres à venir). Mais pour la Piscine 42, je veux retrouver cette connexion directe avec le code - ce plaisir de créer ligne par ligne, sans intermédiaire.

Ce repo contient mon système d'apprentissage pour retrouver l'autonomie complète avant la Piscine 42, et surtout pour le plaisir de coder à nouveau.

## 🚀 Quick Start

### Windows
1. Clone ce repo
2. Double-clic sur `START_42_TRAINING.bat`
3. Suit les instructions dans WSL

### Linux/WSL
```bash
git clone https://github.com/decarvalhoe/42-training.git
cd 42-training
cat REPRENDRE_SESSION.md  # Pour reprendre avec Claude
```

## 📂 Structure

```
42-training/
├── README.md                 # Ce fichier
├── progression.json          # Tracking détaillé de ma progression
├── REPRENDRE_SESSION.md      # Context pour Claude (reprise de session)
├── INSTALLATION_WINDOWS.md   # Guide installation Windows
├── save_progress.sh          # Script de sauvegarde
├── START_42_TRAINING.bat     # Launcher Windows
├── backups/                  # Sauvegardes datées
└── exercises/                # Mes exercices pratiques
    └── hello.txt            # Premier fichier d'exercice
```

## 📈 Progression Actuelle

**Niveau:** 0 (Réapprentissage depuis zéro)
**Phase:** Bash/Terminal basics
**Objectif:** Piscine 42 Lausanne - 22 juin 2026

### ✅ Complété
- [x] Navigation basique (pwd, ls, cd)
- [x] Création dossiers/fichiers (mkdir, touch)
- [x] Renommer/déplacer (mv)

### 🔄 En cours
- [ ] Manipulation fichiers (echo, cat, cp, rm)
- [ ] Pipes et redirections
- [ ] Permissions (chmod)

### 📅 Planning (Progression Accélérée!)

| Période | Focus | Status |
|---------|-------|--------|
| Mars 2026 - Semaine 1-2 | Bash/Terminal basics | 🔄 En cours |
| Mars 2026 - Semaine 3-4 | Scripts Bash avancés | ⏳ À venir |
| Avril 2026 - Semaine 1-2 | Vim + Git mastery | ⏳ À venir |
| Avril 2026 - Semaine 3-4 | C basics (variables, boucles) | ⏳ À venir |
| Mai 2026 - Semaine 1-2 | C pointeurs & mémoire | ⏳ À venir |
| Mai 2026 - Semaine 3-4 | C avancé + Norminette | ⏳ À venir |
| Juin 2026 - Semaine 1-2 | Révisions intensives | ⏳ À venir |
| **22 Juin 2026** | **PISCINE 42 LAUSANNE!** | 🎯 Goal |

## 🧠 Méthode d'apprentissage

### Règles strictes
1. **ZÉRO IA** pendant les exercices
2. Utiliser uniquement `man` pages
3. Apprendre de mes erreurs
4. Répéter jusqu'à la muscle memory
5. Session quotidienne minimum 2h

### Workflow quotidien
```bash
# Matin
./START_42_TRAINING.bat      # Lance WSL + Claude
cat REPRENDRE_SESSION.md     # Reprend où j'étais

# Exercices
# ... pratique sans IA ...

# Soir
./save_progress.sh           # Sauvegarde progression
git add .
git commit -m "Progression du jour"
git push
```

## 🎮 Gamification

| Level | Description | Status |
|-------|-------------|--------|
| 0 | Can't ls without help | ✅ Current |
| 1 | Terminal navigation OK | 🔄 |
| 2 | Pipes & redirections OK | ⏳ |
| 3 | Grep/Sed/Awk OK | ⏳ |
| 4 | Bash scripting OK | ⏳ |
| 5 | C basics OK | ⏳ |
| 10 | READY FOR PISCINE! | 🎯 |

## 📝 Notes d'apprentissage

### Erreurs communes (pour apprendre)
- `ls` pour voir vs `cd` pour entrer
- `echo` seul affiche vs `echo >` écrit dans fichier
- `mkdir` pour dossiers vs `touch` pour fichiers

### Commands essentielles jour 1
```bash
pwd              # Où suis-je?
ls -la           # Tout voir
cd dossier       # Entrer
cd ~             # Home
mkdir nom        # Créer dossier
touch fichier    # Créer fichier vide
echo "txt" > f   # Écrire dans fichier
cat fichier      # Lire fichier
```

## 🤝 Contribution

Ce repo est personnel mais peut aider d'autres candidats 42. N'hésitez pas à:
- ⭐ Star si ça vous aide
- 🍴 Fork pour votre propre préparation
- 💬 Ouvrir une issue pour des suggestions

## 📧 Contact

- GitHub: [@decarvalhoe](https://github.com/decarvalhoe)
- LinkedIn: [Eric de Carvalho](https://www.linkedin.com/in/ericdanieldecarvalho)

## ⚖️ License

MIT - Utilisez librement pour votre préparation 42!

---

**Motto:** *"No IA today, no pain at Piscine"* 💪

*Dernière update: 05/03/2026*