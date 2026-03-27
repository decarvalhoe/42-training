#!/usr/bin/env bash
set -euo pipefail

API_PORT="${API_PORT:-8000}"
AI_GATEWAY_PORT="${AI_GATEWAY_PORT:-8100}"

curl -sf "http://localhost:${API_PORT}/health"
curl -sf "http://localhost:${AI_GATEWAY_PORT}/health"
