#!/usr/bin/env bash
set -euo pipefail

INTERVAL="${1:-900}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_URL="${API_URL:-http://localhost:8000}"
LEARNER_ID="${LEARNER_ID:-default}"
CYCLE=0

echo "Mentor watch - every $((INTERVAL / 60)) min. Ctrl+C to stop."
echo ""

_emit_checkin() {
  curl -sf -X POST "${API_URL}/api/v1/events" \
    -H "Content-Type: application/json" \
    -d "{
      \"event_type\": \"watch_mentor_checkin\",
      \"learner_id\": \"${LEARNER_ID}\",
      \"source_service\": \"api\",
      \"payload\": {\"cycle\": ${CYCLE}, \"interval_seconds\": ${INTERVAL}}
    }" >/dev/null 2>&1 || true
}

while true; do
  CYCLE=$((CYCLE + 1))
  echo "--- cycle ${CYCLE} - $(date '+%H:%M') ---"

  _emit_checkin

  "${SCRIPT_DIR}/ask_mentor.sh" \
    "Periodic check-in: observe the learning session. If the student seems stuck, ask one guiding question and give one hint. If progress is healthy, validate briefly and suggest the next useful check."

  echo ""
  sleep "${INTERVAL}"
done
