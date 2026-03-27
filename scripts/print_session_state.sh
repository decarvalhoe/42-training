#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_FILE="${ROOT_DIR}/progression.json"

python3 - <<'PY' "${STATE_FILE}"
import json
import pathlib
import sys

state_path = pathlib.Path(sys.argv[1])
data = json.loads(state_path.read_text(encoding="utf-8"))

session = data.get("session", {})
progress = data.get("progress", {})

print("=== 42 session state ===")
print(f"Date: {session.get('current_date', 'unknown')}")
print(f"Level: {session.get('level', 'unknown')}")
print(f"Exercise: {progress.get('current_exercise', 'unknown')}")
print(f"Step: {progress.get('current_step', 'unknown')}")
print(f"Next command: {data.get('next_command', 'unknown')}")
print(f"Current directory: {data.get('current_directory', 'unknown')}")
PY
