#!/usr/bin/env bash
# ------------------------------------------------------------------
# build-macos.sh — Build a macOS .dmg for 42-Training
#
# Prerequisites (see docs/MACOS_DISTRIBUTION.md):
#   - macOS 13+
#   - Node.js 20+
#   - Python 3.13+
#   - Xcode Command Line Tools
#
# Usage:
#   ./scripts/build-macos.sh          # Build unsigned .dmg
#   ./scripts/build-macos.sh --sign   # Build + code-sign + notarize
# ------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DESKTOP_DIR="${ROOT_DIR}/desktop"
STAGE_DIR="${DESKTOP_DIR}/staging"
PYTHON="${PYTHON:-python3}"
SIGN=false
RELEASE_VERSION="${RELEASE_VERSION:-}"

if [ -z "${RELEASE_VERSION}" ] && [[ "${GITHUB_REF:-}" == refs/tags/v* ]]; then
  RELEASE_VERSION="${GITHUB_REF#refs/tags/v}"
fi

for arg in "$@"; do
  case "$arg" in
    --sign) SIGN=true ;;
    *) echo "Unknown argument: $arg" >&2; exit 1 ;;
  esac
done

echo "=== 42-Training macOS build ==="
echo "Root:    ${ROOT_DIR}"
echo "Python:  $(${PYTHON} --version 2>&1)"
echo "Node:    $(node --version 2>&1)"
echo "Sign:    ${SIGN}"
echo ""

# ------------------------------------------------------------------
# 1. Clean previous staging
# ------------------------------------------------------------------
echo "[1/6] Cleaning staging directory..."
rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}/backend/api" \
         "${STAGE_DIR}/backend/ai_gateway" \
         "${STAGE_DIR}/frontend" \
         "${STAGE_DIR}/data"

# ------------------------------------------------------------------
# 2. Build Next.js in standalone mode
# ------------------------------------------------------------------
echo "[2/6] Building Next.js frontend (standalone)..."

# Temporarily enable standalone output for the build
NEXT_CONFIG="${ROOT_DIR}/apps/web/next.config.mjs"
NEXT_CONFIG_BACKUP="${NEXT_CONFIG}.bak"
cp "${NEXT_CONFIG}" "${NEXT_CONFIG_BACKUP}"

cat > "${NEXT_CONFIG}" <<'NEXTCONF'
/** @type {import("next").NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
};

export default nextConfig;
NEXTCONF

(cd "${ROOT_DIR}/apps/web" && npm ci --ignore-scripts && npm run build)

# Copy standalone output
cp -R "${ROOT_DIR}/apps/web/.next/standalone/." "${STAGE_DIR}/frontend/"
cp -R "${ROOT_DIR}/apps/web/.next/static" "${STAGE_DIR}/frontend/.next/static"
if [ -d "${ROOT_DIR}/apps/web/public" ]; then
  cp -R "${ROOT_DIR}/apps/web/public" "${STAGE_DIR}/frontend/public"
fi

# Restore original config
mv "${NEXT_CONFIG_BACKUP}" "${NEXT_CONFIG}"

# ------------------------------------------------------------------
# 3. Create Python virtualenvs for backend services
# ------------------------------------------------------------------
echo "[3/6] Creating Python virtualenvs..."

for svc in api ai_gateway; do
  SVC_SRC="${ROOT_DIR}/services/${svc}"
  SVC_DST="${STAGE_DIR}/backend/${svc}"

  ${PYTHON} -m venv "${SVC_DST}/venv"
  "${SVC_DST}/venv/bin/pip" install --quiet --upgrade pip
  "${SVC_DST}/venv/bin/pip" install --quiet -r "${SVC_SRC}/requirements.txt"

  # Copy application code
  cp -R "${SVC_SRC}/app" "${SVC_DST}/app"

  # Copy alembic if present (api service)
  if [ -d "${SVC_SRC}/alembic" ]; then
    cp -R "${SVC_SRC}/alembic" "${SVC_DST}/alembic"
    [ -f "${SVC_SRC}/alembic.ini" ] && cp "${SVC_SRC}/alembic.ini" "${SVC_DST}/alembic.ini"
  fi
done

# ------------------------------------------------------------------
# 4. Copy shared data
# ------------------------------------------------------------------
echo "[4/6] Copying shared data..."
cp "${ROOT_DIR}/packages/curriculum/data/42_lausanne_curriculum.json" "${STAGE_DIR}/data/"
cp "${ROOT_DIR}/progression.json" "${STAGE_DIR}/data/"

# ------------------------------------------------------------------
# 5. Assemble desktop app
# ------------------------------------------------------------------
echo "[5/6] Assembling Electron app..."

# Copy staged assets into desktop/
rm -rf "${DESKTOP_DIR}/backend" "${DESKTOP_DIR}/frontend" "${DESKTOP_DIR}/data"
mv "${STAGE_DIR}/backend"  "${DESKTOP_DIR}/backend"
mv "${STAGE_DIR}/frontend" "${DESKTOP_DIR}/frontend"
mv "${STAGE_DIR}/data"     "${DESKTOP_DIR}/data"
rm -rf "${STAGE_DIR}"

# Install Electron dependencies
(cd "${DESKTOP_DIR}" && npm ci)

if [ -n "${RELEASE_VERSION}" ]; then
  echo "  Applying desktop version: ${RELEASE_VERSION}"
  (cd "${DESKTOP_DIR}" && npm version --no-git-tag-version "${RELEASE_VERSION}")
fi

# ------------------------------------------------------------------
# 6. Build .dmg with electron-builder
# ------------------------------------------------------------------
echo "[6/6] Building .dmg..."

if ${SIGN}; then
  (cd "${DESKTOP_DIR}" && npm run dist:dmg)
else
  (cd "${DESKTOP_DIR}" && CSC_IDENTITY_AUTO_DISCOVERY=false npm run dist:dmg)
fi

echo ""
echo "=== Build complete ==="
echo "Output: ${DESKTOP_DIR}/dist/"
ls -lh "${DESKTOP_DIR}/dist/"*.dmg 2>/dev/null || echo "(no .dmg found — check logs above)"
