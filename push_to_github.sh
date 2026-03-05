#!/bin/bash

echo "=== Push vers GitHub avec authentification ==="
echo ""

# Obtenir le token
TOKEN=$(gh auth token)

# Configurer l'URL avec le token
git remote set-url origin https://decarvalhoe:${TOKEN}@github.com/decarvalhoe/42-training.git

# Push
echo "Pushing to GitHub..."
git push -u origin main

# Nettoyer l'URL (sécurité)
git remote set-url origin https://github.com/decarvalhoe/42-training.git

echo ""
echo "✅ Code poussé sur https://github.com/decarvalhoe/42-training"
echo ""
echo "Tu peux voir ton repo ici :"
echo "https://github.com/decarvalhoe/42-training"