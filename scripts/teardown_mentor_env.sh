#!/usr/bin/env bash
set -euo pipefail

LEARN_SESSION="${LEARN_SESSION:-learn42}"
MENTOR_SESSION="${MENTOR_SESSION:-mentor42}"
WORKSPACE="${HOME}/.42-mentor"
PURGE_TMP=false
PURGE_LOGS=false
QUIET=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --purge-tmp)
      PURGE_TMP=true
      shift
      ;;
    --purge-logs)
      PURGE_LOGS=true
      shift
      ;;
    --purge-all)
      PURGE_TMP=true
      PURGE_LOGS=true
      shift
      ;;
    --quiet)
      QUIET=true
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

log() {
  if ! ${QUIET}; then
    echo "$1"
  fi
}

for session in "${LEARN_SESSION}" "${MENTOR_SESSION}"; do
  if tmux has-session -t "${session}" 2>/dev/null; then
    tmux kill-session -t "${session}"
    log "[+] Killed session ${session}"
  else
    log "[=] Session ${session} already stopped"
  fi
done

if ${PURGE_TMP}; then
  if [[ -d "${WORKSPACE}/tmp" ]]; then
    rm -f "${WORKSPACE}/tmp"/launch-mentor.sh
    rm -f "${WORKSPACE}/tmp"/request-*.md
    rm -f "${WORKSPACE}/tmp"/e2e-response.txt
    log "[+] Purged temporary mentor files"
  fi
fi

if ${PURGE_LOGS}; then
  if [[ -d "${WORKSPACE}/logs" ]]; then
    rm -f "${WORKSPACE}/logs"/*.log
    log "[+] Purged mentor logs"
  fi
fi
