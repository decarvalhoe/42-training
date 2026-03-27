#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${WEB_PORT:-3000}"
cd "${ROOT_DIR}/apps/web"
npm run dev -- --hostname 0.0.0.0 --port "${PORT}"
