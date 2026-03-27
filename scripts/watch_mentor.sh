#!/usr/bin/env bash
set -euo pipefail

INTERVAL="${1:-900}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CYCLE=0

echo "Mentor watch - every $((INTERVAL / 60)) min. Ctrl+C to stop."
echo ""

while true; do
  CYCLE=$((CYCLE + 1))
  echo "--- cycle ${CYCLE} - $(date '+%H:%M') ---"

  "${SCRIPT_DIR}/ask_mentor.sh" \
    "Periodic check-in: observe the learning session. If the student seems stuck, ask one guiding question and give one hint. If progress is healthy, validate briefly and suggest the next useful check."

  echo ""
  sleep "${INTERVAL}"
done
