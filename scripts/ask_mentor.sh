#!/usr/bin/env bash
set -euo pipefail

CLAUDE_BIN="${CLAUDE_BIN:-}"
if [[ -z "${CLAUDE_BIN}" ]]; then
  for candidate in "${HOME}/.local/bin/claude" "${HOME}/.claude/bin/claude" /usr/local/bin/claude; do
    if [[ -x "${candidate}" ]]; then
      CLAUDE_BIN="${candidate}"
      break
    fi
  done
  [[ -z "${CLAUDE_BIN}" ]] && CLAUDE_BIN="claude"
fi

LEARN_SESSION="${LEARN_SESSION:-learn42}"
MENTOR_SESSION="${MENTOR_SESSION:-mentor42}"
WORKSPACE="${HOME}/.42-mentor"
KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROMPT_FILE="${KIT_ROOT}/prompts/mentor_system_prompt.txt"

FILES=()
QUESTION=""
SESSION_MODE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --file)
      [[ $# -lt 2 ]] && { echo "Missing value for --file" >&2; exit 1; }
      FILES+=("$2")
      shift 2
      ;;
    --session|-s)
      SESSION_MODE=true
      shift
      ;;
    *)
      QUESTION="$*"
      break
      ;;
  esac
done

[[ -z "${QUESTION}" ]] && QUESTION="Observe my current work session and give pedagogical feedback."

CONTEXT=""
if tmux has-session -t "${LEARN_SESSION}" 2>/dev/null; then
  LEARN_PATH="$(tmux display-message -p -t "${LEARN_SESSION}:work" '#{pane_current_path}' 2>/dev/null || echo "$PWD")"
  CONTEXT+="# Student work context
Project: ${LEARN_PATH}
Time: $(date '+%Y-%m-%d %H:%M:%S')
"

  if git -C "${LEARN_PATH}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    CONTEXT+="
## Git status
$(git -C "${LEARN_PATH}" status --short 2>/dev/null || true)
"
  fi

  for win in work build tests; do
    PANE_CONTENT="$(tmux capture-pane -t "${LEARN_SESSION}:${win}" -p -S -60 2>/dev/null || true)"
    if [[ -n "${PANE_CONTENT}" ]]; then
      CONTEXT+="
## Terminal: ${win}
${PANE_CONTENT}
"
    fi
  done
else
  LEARN_PATH="$PWD"
  CONTEXT="# No learn42 session found
Project: ${LEARN_PATH}
"
fi

for file in "${FILES[@]}"; do
  FULL=""
  if [[ -f "${LEARN_PATH}/${file}" ]]; then
    FULL="${LEARN_PATH}/${file}"
  elif [[ -f "${file}" ]]; then
    FULL="${file}"
  fi

  if [[ -n "${FULL}" ]]; then
    CONTEXT+="
## File: ${file}
$(head -300 "${FULL}")
"
  else
    CONTEXT+="
## File: ${file} - NOT FOUND
"
  fi
done

FULL_PROMPT="${CONTEXT}

# Student question
${QUESTION}

# Response rules
- Do not provide the full solution unless explicitly asked.
- Start with what you observe.
- Ask one useful question.
- Give one hint.
- End with one concrete next action.
- Answer in French."

mkdir -p "${WORKSPACE}/tmp"
REQ_FILE="${WORKSPACE}/tmp/request-$(date +%Y%m%d-%H%M%S)-$$.md"
printf '%s\n' "${FULL_PROMPT}" > "${REQ_FILE}"

if ${SESSION_MODE}; then
  if ! tmux has-session -t "${MENTOR_SESSION}" 2>/dev/null; then
    echo "Session ${MENTOR_SESSION} not found." >&2
    exit 1
  fi

  tmux send-keys -t "${MENTOR_SESSION}:mentor" \
    "Read ${REQ_FILE} and respond following the mentor system prompt." C-m
  echo "Sent to ${MENTOR_SESSION}."
else
  SYSTEM_PROMPT=""
  [[ -f "${PROMPT_FILE}" ]] && SYSTEM_PROMPT="$(cat "${PROMPT_FILE}")"

  echo "----- mentor -----"
  if [[ -n "${SYSTEM_PROMPT}" ]]; then
    printf '%s\n' "${FULL_PROMPT}" | "${CLAUDE_BIN}" -p --system-prompt "${SYSTEM_PROMPT}" 2>/dev/null
  else
    printf '%s\n' "${FULL_PROMPT}" | "${CLAUDE_BIN}" -p 2>/dev/null
  fi
  echo "------------------"
fi
