#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="${C_QUALITY_TARGETS_FILE:-${ROOT_DIR}/.github/c-quality-targets.json}"
MODE="${1:-all}"

usage() {
  echo "Usage: bash scripts/run_c_quality_checks.sh [norminette|moulinette|all]" >&2
}

json_array_to_lines() {
  python3 - "$1" <<'PY'
import json
import sys

for item in json.loads(sys.argv[1]):
    print(item)
PY
}

load_projects() {
  python3 - "$CONFIG_FILE" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    config = json.load(fh)

for project in config.get("projects", []):
    print(
        "\t".join(
            (
                project["name"],
                project["path"],
                json.dumps(project.get("norminette", [])),
                json.dumps(project.get("moulinette", [])),
            )
        )
    )
PY
}

run_norminette() {
  local name="$1"
  local project_dir="$2"
  local norm_json="$3"
  local -a entries=()

  mapfile -t entries < <(json_array_to_lines "$norm_json")
  if [[ ${#entries[@]} -eq 0 ]]; then
    mapfile -t entries < <(cd "$project_dir" && find . -type f \( -name '*.c' -o -name '*.h' \) | sort)
  fi

  if [[ ${#entries[@]} -eq 0 ]]; then
    echo "No C source files found for ${name}" >&2
    exit 1
  fi

  echo "==> Norminette: ${name}"
  (
    cd "$project_dir"
    norminette "${entries[@]}"
  )
}

run_moulinette() {
  local name="$1"
  local project_dir="$2"
  local moulinette_json="$3"
  local -a commands=()

  mapfile -t commands < <(json_array_to_lines "$moulinette_json")
  if [[ ${#commands[@]} -eq 0 ]]; then
    echo "No moulinette commands configured for ${name}" >&2
    exit 1
  fi

  echo "==> Moulinette-style checks: ${name}"
  for command in "${commands[@]}"; do
    echo "+ ${command}"
    (
      cd "$project_dir"
      bash -lc "$command"
    )
  done
}

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Missing C quality config: ${CONFIG_FILE}" >&2
  exit 1
fi

case "$MODE" in
  norminette|moulinette|all)
    ;;
  *)
    usage
    exit 1
    ;;
esac

mapfile -t PROJECTS < <(load_projects)
if [[ ${#PROJECTS[@]} -eq 0 ]]; then
  echo "No C quality targets configured. Skipping."
  exit 0
fi

for project in "${PROJECTS[@]}"; do
  IFS=$'\t' read -r name relative_path norm_json moulinette_json <<< "$project"
  project_dir="${ROOT_DIR}/${relative_path}"

  if [[ ! -d "$project_dir" ]]; then
    echo "Configured C quality target is missing: ${relative_path}" >&2
    exit 1
  fi

  case "$MODE" in
    norminette)
      run_norminette "$name" "$project_dir" "$norm_json"
      ;;
    moulinette)
      run_moulinette "$name" "$project_dir" "$moulinette_json"
      ;;
    all)
      run_norminette "$name" "$project_dir" "$norm_json"
      run_moulinette "$name" "$project_dir" "$moulinette_json"
      ;;
  esac
done
