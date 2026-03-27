#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-$PWD}"
LEARN_SESSION="${LEARN_SESSION:-learn42}"
MENTOR_SESSION="${MENTOR_SESSION:-mentor42}"
KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE="${HOME}/.42-mentor"
PROMPT_FILE="${KIT_ROOT}/prompts/mentor_system_prompt.txt"

if [[ ! -d "${PROJECT_DIR}" ]]; then
  echo "Project directory not found: ${PROJECT_DIR}" >&2
  exit 1
fi
PROJECT_DIR="$(cd "${PROJECT_DIR}" && pwd)"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is required. Run ./scripts/bootstrap_ubuntu_42.sh first." >&2
  exit 1
fi

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

if [[ "${CLAUDE_BIN}" == */* ]]; then
  if [[ ! -x "${CLAUDE_BIN}" ]]; then
    echo "Claude CLI not found at ${CLAUDE_BIN}" >&2
    exit 1
  fi
elif ! command -v "${CLAUDE_BIN}" >/dev/null 2>&1; then
  echo "Claude CLI not found. Install it or set CLAUDE_BIN." >&2
  exit 1
fi

mkdir -p "${WORKSPACE}/logs" "${WORKSPACE}/tmp"

if ! tmux has-session -t "${LEARN_SESSION}" 2>/dev/null; then
  tmux new-session -d -s "${LEARN_SESSION}" -n work -c "${PROJECT_DIR}"
  tmux new-window -t "${LEARN_SESSION}" -n build -c "${PROJECT_DIR}"
  tmux new-window -t "${LEARN_SESSION}" -n tests -c "${PROJECT_DIR}"
  tmux select-window -t "${LEARN_SESSION}:work"

  for win in work build tests; do
    tmux pipe-pane -o -t "${LEARN_SESSION}:${win}" \
      "cat >> '${WORKSPACE}/logs/${LEARN_SESSION}-${win}.log'"
  done

  echo "[+] Created session ${LEARN_SESSION}"
else
  echo "[=] Session ${LEARN_SESSION} already exists"
fi

if ! tmux has-session -t "${MENTOR_SESSION}" 2>/dev/null; then
  tmux new-session -d -s "${MENTOR_SESSION}" -n mentor -c "${PROJECT_DIR}"

  LAUNCHER="${WORKSPACE}/tmp/launch-mentor.sh"
  if [[ -f "${PROMPT_FILE}" ]]; then
    cat > "${LAUNCHER}" <<LAUNCH_EOF
#!/usr/bin/env bash
exec ${CLAUDE_BIN} --system-prompt "\$(cat '${PROMPT_FILE}')"
LAUNCH_EOF
  else
    cat > "${LAUNCHER}" <<LAUNCH_EOF
#!/usr/bin/env bash
exec ${CLAUDE_BIN}
LAUNCH_EOF
  fi

  chmod +x "${LAUNCHER}"
  tmux send-keys -t "${MENTOR_SESSION}:mentor" "bash ${LAUNCHER}" C-m

  echo "[+] Created session ${MENTOR_SESSION}"
else
  echo "[=] Session ${MENTOR_SESSION} already exists"
fi

ALIAS_FILE="${HOME}/.42-mentor-aliases"
cat > "${ALIAS_FILE}" <<ALIASES
alias m='${KIT_ROOT}/scripts/ask_mentor.sh'
alias mw='${KIT_ROOT}/scripts/watch_mentor.sh'
alias ms='tmux switch-client -t ${MENTOR_SESSION}'
alias ml='tmux switch-client -t ${LEARN_SESSION}'
ALIASES

if ! grep -qF '.42-mentor-aliases' "${HOME}/.bashrc" 2>/dev/null; then
  echo "[ -f ~/.42-mentor-aliases ] && source ~/.42-mentor-aliases" >> "${HOME}/.bashrc"
fi

cat <<EOF

Ready.

Sessions:
  ${LEARN_SESSION}  - work / build / tests
  ${MENTOR_SESSION} - mentor

Shortcuts after 'source ~/.bashrc':
  m "question"
  m --file file.c "question"
  m --session "question"
  mw
  ms
  ml

EOF
