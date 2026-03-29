#!/usr/bin/env bash
# generate-changelog.sh — Append git log entries to CHANGELOG.md [Unreleased] section.
#
# Usage:
#   ./scripts/generate-changelog.sh              # since last tag
#   ./scripts/generate-changelog.sh v0.1.0       # since specific tag
#   ./scripts/generate-changelog.sh --dry-run    # print without writing
#
# Categorises commits by conventional-commit prefix:
#   feat:     → Added
#   fix:      → Fixed
#   refactor: → Changed
#   docs:     → Changed
#   other     → Changed

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
CHANGELOG="$REPO_ROOT/CHANGELOG.md"
DRY_RUN=false
SINCE_TAG=""

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    *)         SINCE_TAG="$arg" ;;
  esac
done

# Determine range
if [ -z "$SINCE_TAG" ]; then
  SINCE_TAG=$(git tag --sort=-creatordate | head -1 || true)
fi

if [ -n "$SINCE_TAG" ]; then
  RANGE="${SINCE_TAG}..HEAD"
  echo "Generating changelog since $SINCE_TAG"
else
  RANGE="HEAD"
  echo "Generating changelog for all commits (no tags found)"
fi

# Collect commits by category
ADDED=""
FIXED=""
CHANGED=""

while IFS= read -r line; do
  [ -z "$line" ] && continue
  subject="${line#* }"
  if [[ "$subject" =~ ^feat ]]; then
    ADDED+="- ${subject}"$'\n'
  elif [[ "$subject" =~ ^fix ]]; then
    FIXED+="- ${subject}"$'\n'
  else
    CHANGED+="- ${subject}"$'\n'
  fi
done < <(git log "$RANGE" --pretty=format:"%h %s" --no-merges 2>/dev/null)

# Format output
OUTPUT=""
if [ -n "$ADDED" ]; then
  OUTPUT+="### Added"$'\n'"$ADDED"$'\n'
fi
if [ -n "$CHANGED" ]; then
  OUTPUT+="### Changed"$'\n'"$CHANGED"$'\n'
fi
if [ -n "$FIXED" ]; then
  OUTPUT+="### Fixed"$'\n'"$FIXED"$'\n'
fi

if [ -z "$OUTPUT" ]; then
  echo "No new commits found."
  exit 0
fi

echo ""
echo "=== Generated entries ==="
echo ""
echo "$OUTPUT"

if [ "$DRY_RUN" = true ]; then
  echo "(dry run — nothing written)"
  exit 0
fi

if [ ! -f "$CHANGELOG" ]; then
  echo "CHANGELOG.md not found at $CHANGELOG"
  exit 1
fi

# Insert after ## [Unreleased] line
MARKER="## \\[Unreleased\\]"
if grep -q "$MARKER" "$CHANGELOG"; then
  TMPFILE=$(mktemp)
  awk -v new="$OUTPUT" "
    /$MARKER/ { print; print \"\"; print new; next }
    { print }
  " "$CHANGELOG" > "$TMPFILE"
  mv "$TMPFILE" "$CHANGELOG"
  echo "Updated $CHANGELOG"
else
  echo "No [Unreleased] section found in CHANGELOG.md"
  exit 1
fi
