#!/usr/bin/env bash
set -euo pipefail

echo "=== 42 Training - Ubuntu bootstrap ==="
echo ""

echo "[1/4] Updating packages"
sudo apt update -qq

echo "[2/4] Installing core tools"
sudo apt install -y -qq \
  build-essential \
  clang \
  curl \
  gdb \
  git \
  make \
  python3 \
  python3-pip \
  ripgrep \
  shellcheck \
  tmux \
  tree \
  valgrind

echo "[3/4] Checking Claude CLI"
if command -v claude >/dev/null 2>&1; then
  echo "  claude already installed: $(claude --version 2>&1 | head -1)"
else
  echo "  Claude CLI missing."
  echo "  Install Node.js 18+ then run: npm install -g @anthropic-ai/claude-code"
fi

echo "[4/4] Creating runtime directories"
mkdir -p "${HOME}/.42-mentor/logs" "${HOME}/.42-mentor/tmp"

cat <<'EOF'

Done.

Next:
  1. cd ~/42-training
  2. ./scripts/setup_github_auth.sh   # optional
  3. ./scripts/doctor.sh
  4. ./scripts/print_session_state.sh
  5. ./scripts/start_42_mentor_env.sh .

EOF
