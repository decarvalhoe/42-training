#!/usr/bin/env bash
# dev-up.sh — Start the full dev stack via docker-compose.
# Linux-first. Requires: docker, docker-compose (or docker compose plugin).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# --- Detect compose command ---
if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  echo "ERROR: docker compose not found. Install Docker with the compose plugin."
  exit 1
fi

# --- Copy .env.example -> .env where missing ---
for dir in services/api services/ai_gateway apps/web; do
  if [ -f "$dir/.env.example" ] && [ ! -f "$dir/.env" ]; then
    cp "$dir/.env.example" "$dir/.env"
    echo "Created $dir/.env from .env.example"
  fi
done

# --- Start services ---
echo "Starting dev stack..."
$COMPOSE up -d --build

# --- Wait for healthchecks ---
echo "Waiting for services to become healthy..."
TIMEOUT=120
ELAPSED=0
INTERVAL=5

while [ "$ELAPSED" -lt "$TIMEOUT" ]; do
  UNHEALTHY=$($COMPOSE ps --format json 2>/dev/null \
    | grep -c '"Health":"starting"' || true)
  HEALTH_STATUS=$($COMPOSE ps 2>/dev/null)

  if echo "$HEALTH_STATUS" | grep -q "(unhealthy)"; then
    echo "ERROR: A service is unhealthy."
    $COMPOSE ps
    exit 1
  fi

  if [ "$UNHEALTHY" -eq 0 ] && ! echo "$HEALTH_STATUS" | grep -q "(health: starting)"; then
    break
  fi

  sleep "$INTERVAL"
  ELAPSED=$((ELAPSED + INTERVAL))
done

if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
  echo "WARNING: Timed out waiting for healthchecks (${TIMEOUT}s)."
  $COMPOSE ps
  exit 1
fi

# --- Print service URLs ---
echo ""
echo "=== Dev stack is up ==="
echo "  Web:        http://localhost:3000"
echo "  API:        http://localhost:8000"
echo "  AI Gateway: http://localhost:8100"
echo "  Postgres:   localhost:5432 (training/training)"
echo "  Redis:      localhost:6379"
echo ""
echo "Logs:  $COMPOSE logs -f"
echo "Stop:  $COMPOSE down"
