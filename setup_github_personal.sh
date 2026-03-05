#!/bin/bash

echo "========================================="
echo "  Configuration GitHub - decarvalhoe"
echo "========================================="
echo ""
echo "Je vais lancer gh auth login."
echo "Suis ces étapes :"
echo ""
echo "1. Choisis: GitHub.com"
echo "2. Protocole: SSH (recommandé)"
echo "3. Génère une nouvelle clé SSH : Yes"
echo "4. Passphrase : Appuie sur Enter (pas de passphrase)"
echo "5. Titre pour la clé : decarvalhoe-42-training"
echo "6. Authentification : Login with a web browser"
echo ""
echo "Appuie sur ENTER pour commencer..."
read

# Lance l'authentification
gh auth login

echo ""
echo "========================================="
echo "Vérification du nouveau compte..."
gh auth status

echo ""
echo "Si tout est OK, on peut maintenant créer le repo !"