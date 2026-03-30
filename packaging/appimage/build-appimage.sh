#!/usr/bin/env bash
# Build an AppImage for 42-training.
# Self-contained bundle with embedded Python, Node, and all services.
# Usage: ./packaging/appimage/build-appimage.sh [version]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="${1:-0.1.0}"
PKG_NAME="42-training"
APPDIR="$REPO_ROOT/packaging/appimage/_build/${PKG_NAME}.AppDir"

echo "==> Building ${PKG_NAME}-${VERSION}.AppImage"

# Download appimagetool if not present
APPIMAGETOOL="$REPO_ROOT/packaging/appimage/appimagetool"
if [ ! -x "$APPIMAGETOOL" ]; then
    echo "    Downloading appimagetool..."
    curl -sSL -o "$APPIMAGETOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$APPIMAGETOOL"
fi

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/opt/42-training"
mkdir -p "$APPDIR/opt/42-training/apps/web"
mkdir -p "$APPDIR/opt/42-training/packages/curriculum"

# --- Desktop entry ---
cat > "$APPDIR/${PKG_NAME}.desktop" <<EOF
[Desktop Entry]
Name=42-training
Comment=42 Lausanne learning platform
Exec=42-training-launcher
Icon=42-training
Terminal=true
Type=Application
Categories=Education;Development;
EOF

# --- Icon (simple SVG placeholder) ---
cat > "$APPDIR/42-training.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="12" fill="#1c1a17"/>
  <text x="32" y="42" text-anchor="middle" fill="#d8a657"
        font-family="monospace" font-size="24" font-weight="bold">42</text>
</svg>
SVG
cp "$APPDIR/42-training.svg" "$APPDIR/.DirIcon"

# --- AppRun launcher ---
cat > "$APPDIR/AppRun" <<'APPRUN'
#!/usr/bin/env bash
set -euo pipefail

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="$SELF_DIR/usr/bin:$PATH"
export PYTHONPATH="$SELF_DIR/opt/42-training/services/api:$SELF_DIR/opt/42-training/services/ai_gateway"

APP_DIR="$SELF_DIR/opt/42-training"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/42-training"
mkdir -p "$DATA_DIR"

# Copy default progression if not present
if [ ! -f "$DATA_DIR/progression.json" ]; then
    cp "$APP_DIR/progression.json" "$DATA_DIR/"
fi

case "${1:-start}" in
    start)
        echo "Starting 42-training services..."
        echo "  API:     http://localhost:8000"
        echo "  Gateway: http://localhost:8100"
        echo "  Web:     http://localhost:3000"
        echo ""

        # Start API
        cd "$APP_DIR/services/api"
        "$APP_DIR/services/api/.venv/bin/uvicorn" app.main:app \
            --host 127.0.0.1 --port 8000 &
        API_PID=$!

        # Start AI Gateway
        cd "$APP_DIR/services/ai_gateway"
        "$APP_DIR/services/ai_gateway/.venv/bin/uvicorn" app.main:app \
            --host 127.0.0.1 --port 8100 &
        GW_PID=$!

        # Start Web
        cd "$APP_DIR/apps/web"
        npm run start &
        WEB_PID=$!

        echo "PIDs: api=$API_PID gateway=$GW_PID web=$WEB_PID"
        echo "Press Ctrl+C to stop all services."

        trap "kill $API_PID $GW_PID $WEB_PID 2>/dev/null; exit 0" INT TERM
        wait
        ;;
    stop)
        pkill -f "42-training" || true
        echo "Services stopped."
        ;;
    *)
        echo "Usage: 42-training {start|stop}"
        ;;
esac
APPRUN
chmod +x "$APPDIR/AppRun"

# --- Copy application ---
rsync -a --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
    --exclude='.next' --exclude='.venv' --exclude='*.pyc' --exclude='tests' \
    "$REPO_ROOT/services/" "$APPDIR/opt/42-training/services/"
rsync -a --exclude='node_modules' --exclude='.next' \
    "$REPO_ROOT/apps/web/" "$APPDIR/opt/42-training/apps/web/"
cp -r "$REPO_ROOT/packages/curriculum/data" "$APPDIR/opt/42-training/packages/curriculum/data"
cp "$REPO_ROOT/progression.json" "$APPDIR/opt/42-training/"

echo "==> AppDir assembled at $APPDIR"
OUTPUT="$REPO_ROOT/packaging/appimage/${PKG_NAME}-${VERSION}-x86_64.AppImage"
rm -f "$OUTPUT"
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$APPIMAGETOOL" "$APPDIR" "$OUTPUT"

echo "==> Built: $OUTPUT"
