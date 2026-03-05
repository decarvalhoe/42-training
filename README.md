# 🎯 42-training - Préparation Piscine 42 Lausanne

> **Objectif:** Réapprendre les bases depuis ZÉRO pour la Piscine 42 Lausanne (Juin 2026)

## 📊 Contexte

Après des années à utiliser des agents IA (Claude, Copilot, etc.), j'ai perdu mes compétences de codage "bare metal". Ce repo contient mon système d'apprentissage pour retrouver l'autonomie complète avant la Piscine.

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

### 📅 Planning

| Période | Focus | Status |
|---------|-------|--------|
| Mars-Avril 2026 | Bash/Terminal | 🔄 En cours |
| Mai-Juin 2026 | Scripts Bash | ⏳ À venir |
| Juillet-Août 2026 | C basics | ⏳ À venir |
| Sept-Oct 2026 | C avancé + pointeurs | ⏳ À venir |
| Nov-Déc 2026 | Algorithmes | ⏳ À venir |
| Jan-Mars 2027 | Projets 42 style | ⏳ À venir |
| Avril-Mai 2027 | Norminette + Exam prep | ⏳ À venir |
| **22 Juin 2027** | **PISCINE!** | 🎯 Goal |

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