#!/usr/bin/env bash
set -euo pipefail

echo "=== GitHub auth setup ==="
echo ""
echo "This helper keeps the repository on a normal remote URL."
echo "Use GitHub CLI or SSH, but do not inject tokens into origin."
echo ""

gh auth login
echo ""
gh auth status
