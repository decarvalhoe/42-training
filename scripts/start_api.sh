#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${API_PORT:-8000}"
cd "${ROOT_DIR}/services/api"
uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --reload
