#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${API_PORT:-8000}"
DB_PATH="${API_E2E_DB_PATH:-${ROOT_DIR}/.tmp/playwright/api.sqlite3}"

mkdir -p "$(dirname "${DB_PATH}")"
rm -f "${DB_PATH}"

export DATA_ROOT="${DATA_ROOT:-${ROOT_DIR}}"
export CORS_ALLOW_ORIGINS="${CORS_ALLOW_ORIGINS:-http://127.0.0.1:3000,http://localhost:3000}"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///${DB_PATH}}"

cd "${ROOT_DIR}/services/api"
if [ -f ".venv/bin/activate" ]; then
  # Prefer the repo-local runtime when available so Playwright can boot the API from a clean WSL clone.
  . ".venv/bin/activate"
fi
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port "${PORT}"
