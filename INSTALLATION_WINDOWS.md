# 🚀 INSTALLATION LAUNCHER 42 TRAINING - WINDOWS

## 📍 ÉTAPES D'INSTALLATION

### 1️⃣ Créer un raccourci sur le Bureau Windows

1. Ouvre l'Explorateur Windows
2. Va dans: `\\wsl$\Ubuntu\home\decarvalhoe\42_training\`
3. Trouve le fichier `START_42_TRAINING.bat`
4. Clic droit → "Envoyer vers" → "Bureau (créer un raccourci)"

### 2️⃣ OU Copier directement le launcher

```powershell
# Dans PowerShell (en admin):
copy \\wsl$\Ubuntu\home\decarvalhoe\42_training\START_42_TRAINING.bat C:\Users\%USERNAME%\Desktop\
```

## 🎯 UTILISATION

### Pour commencer une session:
1. Double-clique sur `START_42_TRAINING.bat` sur ton bureau
2. Ça ouvre WSL + Claude automatiquement
3. Dans WSL, tape: `cat REPRENDRE_SESSION.md`
4. Copie le contexte dans Claude
5. Continue où tu en étais !

### Pour sauvegarder avant de fermer:
```bash
# Dans WSL, toujours faire:
cd ~/42_training
./save_progress.sh
```

## 📂 STRUCTURE DES FICHIERS

```
42_training/
├── progression.json          # État actuel (JSON)
├── REPRENDRE_SESSION.md      # Contexte pour Claude
├── save_progress.sh          # Script de sauvegarde
├── START_42_TRAINING.bat     # Launcher Windows
├── hello.txt                 # Fichier d'exercice
└── backups/                  # Sauvegardes datées
    └── progression_*.json
```

## 🔄 WORKFLOW QUOTIDIEN

1. **MATIN:** Double-clic sur launcher → WSL + Claude s'ouvrent
2. **SESSION:** Tu fais tes exercices avec Claude
3. **PAUSE:** `./save_progress.sh` pour sauvegarder
4. **REPRISE:** `cat REPRENDRE_SESSION.md` et copier dans Claude

## ⚡ COMMANDES RAPIDES

```bash
# Voir où j'en suis
cat progression.json | jq .progress.current_step

# Voir mes erreurs pour apprendre
cat progression.json | jq .mistakes

# Backup manuel
cp progression.json progression_backup_$(date +%Y%m%d).json
```

## 🆘 PROBLÈMES COURANTS

**"WSL ne démarre pas"**
→ Ouvre PowerShell en admin: `wsl --install`

**"Fichier .bat ne marche pas"**
→ Clic droit → "Exécuter en tant qu'administrateur"

**"Je ne trouve pas mes fichiers"**
→ Depuis Windows: `\\wsl$\Ubuntu\home\decarvalhoe\42_training\`
→ Depuis WSL: `cd ~/42_training`

---

**READY TO GO!** 🚀 Redémarre et utilise le launcher!