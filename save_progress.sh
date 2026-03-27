#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${ROOT_DIR}/backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== SAUVEGARDE PROGRESSION 42 ===${NC}"
echo ""

mkdir -p "${BACKUP_DIR}"

echo -e "${YELLOW}Sauvegarde historique shell...${NC}"
history | tail -50 > "${HOME}/.42_history_backup" || true

cp "${ROOT_DIR}/progression.json" "${BACKUP_DIR}/progression_${TIMESTAMP}.json"

echo -e "${GREEN}Progression sauvegardee.${NC}"
echo "Backup: ${BACKUP_DIR}/progression_${TIMESTAMP}.json"
echo ""
echo -e "${YELLOW}Etat courant:${NC}"
"${ROOT_DIR}/scripts/print_session_state.sh" || true
