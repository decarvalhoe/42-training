#!/bin/bash

# Script de sauvegarde progression 42
# À exécuter avant de fermer la session

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== SAUVEGARDE PROGRESSION 42 ===${NC}"
echo ""

# Sauvegarde de l'historique des commandes du jour
echo -e "${YELLOW}Sauvegarde historique...${NC}"
history | tail -50 > ~/.42_history_backup

# Update timestamp dans progression.json
current_date=$(date +%Y-%m-%d)
current_time=$(date +%H:%M)

# Créer un backup daté
backup_dir="$HOME/42_training/backups"
mkdir -p "$backup_dir"
cp progression.json "$backup_dir/progression_${current_date}_${current_time}.json"

echo -e "${GREEN}✓ Progression sauvegardée${NC}"
echo ""
echo "Fichiers de sauvegarde:"
echo "- progression.json (état actuel)"
echo "- REPRENDRE_SESSION.md (pour Claude)"
echo "- backups/progression_${current_date}_${current_time}.json"
echo ""
echo -e "${YELLOW}Pour reprendre après redémarrage:${NC}"
echo "1. Ouvre WSL"
echo "2. cd ~/42_training"
echo "3. cat REPRENDRE_SESSION.md"
echo "4. Copie le contexte dans Claude"
echo ""
echo -e "${GREEN}Bonne pause !${NC}"