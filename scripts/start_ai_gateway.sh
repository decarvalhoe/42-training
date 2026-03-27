#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${AI_GATEWAY_PORT:-8100}"
cd "${ROOT_DIR}/services/ai_gateway"
uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --reload
