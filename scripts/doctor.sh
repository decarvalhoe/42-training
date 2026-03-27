#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_FILE="${ROOT_DIR}/progression.json"
PROMPT_FILE="${ROOT_DIR}/prompts/mentor_system_prompt.txt"
GITATTR_FILE="${ROOT_DIR}/.gitattributes"
LEARN_SESSION="${LEARN_SESSION:-learn42}"
MENTOR_SESSION="${MENTOR_SESSION:-mentor42}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

FAILURES=0
WARNINGS=0

pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; WARNINGS=$((WARNINGS+1)); }
fail() { echo -e "${RED}[FAIL]${NC} $1"; FAILURES=$((FAILURES+1)); }
info() { echo -e "${CYAN}[INFO]${NC} $1"; }

check_required_cmd() {
  local cmd="$1"
  if command -v "${cmd}" >/dev/null 2>&1; then
    pass "command '${cmd}' found: $(command -v "${cmd}")"
  else
    fail "command '${cmd}' missing"
  fi
}

check_optional_cmd() {
  local cmd="$1"
  if command -v "${cmd}" >/dev/null 2>&1; then
    pass "command '${cmd}' found: $(command -v "${cmd}")"
  else
    warn "command '${cmd}' missing"
  fi
}

info "Checking runtime"
if [[ "$(uname -s)" == "Linux" ]]; then
  pass "Linux runtime detected"
else
  fail "Linux runtime required"
fi

if grep -qi "microsoft" /proc/version 2>/dev/null; then
  pass "WSL environment detected"
else
  pass "native Linux environment detected"
fi

info "Checking commands"
check_required_cmd git
check_required_cmd python3
check_required_cmd tmux
check_required_cmd bash
check_optional_cmd claude
check_optional_cmd shellcheck

info "Checking repository files"
[[ -f "${STATE_FILE}" ]] && pass "progression.json present" || fail "progression.json missing"
[[ -f "${PROMPT_FILE}" ]] && pass "mentor prompt present" || fail "mentor prompt missing"
[[ -f "${GITATTR_FILE}" ]] && pass ".gitattributes present" || fail ".gitattributes missing"

if git -C "${ROOT_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  pass "git repository detected"
else
  fail "repository is not a git checkout"
fi

if git -C "${ROOT_DIR}" remote get-url origin >/dev/null 2>&1; then
  pass "origin remote configured"
else
  warn "origin remote missing"
fi

if [[ "${ROOT_DIR}" == "${HOME}/42-training" ]]; then
  pass "canonical path in use: ${ROOT_DIR}"
elif [[ "${ROOT_DIR}" == /mnt/* ]]; then
  pass "WSL-mounted repository path detected: ${ROOT_DIR}"
else
  warn "repository path is ${ROOT_DIR}; expected ${HOME}/42-training"
fi

info "Checking progression state"
if python3 - <<'PY' "${STATE_FILE}"
import json
import pathlib
import sys

state_path = pathlib.Path(sys.argv[1])
data = json.loads(state_path.read_text(encoding="utf-8"))
assert "session" in data
assert "progress" in data
assert isinstance(data.get("progress", {}).get("completed", []), list)
assert isinstance(data.get("progress", {}).get("in_progress", []), list)
assert isinstance(data.get("progress", {}).get("todo", []), list)
PY
then
  pass "progression.json is valid"
else
  fail "progression.json is invalid"
fi

info "Checking line endings"
if python3 - <<'PY' "${ROOT_DIR}"
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
bad = []
for path in sorted(root.rglob("*")):
    if not path.is_file():
        continue
    if path.suffix not in {".sh", ".md", ".json", ".txt"}:
        continue
    if b"\r" in path.read_bytes():
        bad.append(str(path))

if bad:
    print("\n".join(bad))
    raise SystemExit(1)
PY
then
  pass "LF-only text files confirmed"
else
  warn "CRLF detected in tracked text files"
fi

info "Checking mentor sessions"
if tmux has-session -t "${LEARN_SESSION}" 2>/dev/null; then
  pass "session '${LEARN_SESSION}' is running"
else
  warn "session '${LEARN_SESSION}' is not running"
fi

if tmux has-session -t "${MENTOR_SESSION}" 2>/dev/null; then
  pass "session '${MENTOR_SESSION}' is running"
else
  warn "session '${MENTOR_SESSION}' is not running"
fi

echo ""
if [[ ${FAILURES} -eq 0 ]]; then
  echo -e "${GREEN}Doctor completed: ${FAILURES} failure(s), ${WARNINGS} warning(s).${NC}"
else
  echo -e "${RED}Doctor completed: ${FAILURES} failure(s), ${WARNINGS} warning(s).${NC}"
fi

exit "${FAILURES}"
