#!/usr/bin/env bash
# Build a .deb package for 42-training (Debian/Ubuntu).
# Usage: ./packaging/deb/build-deb.sh [version]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="${1:-0.1.0}"
PKG_NAME="42-training"
ARCH="amd64"
BUILD_DIR="$REPO_ROOT/packaging/deb/_build/${PKG_NAME}_${VERSION}_${ARCH}"

echo "==> Building ${PKG_NAME}_${VERSION}_${ARCH}.deb"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/opt/42-training/services/api"
mkdir -p "$BUILD_DIR/opt/42-training/services/ai_gateway"
mkdir -p "$BUILD_DIR/opt/42-training/apps/web"
mkdir -p "$BUILD_DIR/opt/42-training/packages/curriculum/data"
mkdir -p "$BUILD_DIR/opt/42-training/scripts"
mkdir -p "$BUILD_DIR/etc/42-training"
mkdir -p "$BUILD_DIR/usr/lib/systemd/system"
mkdir -p "$BUILD_DIR/usr/bin"

# --- Control file ---
cat > "$BUILD_DIR/DEBIAN/control" <<EOF
Package: ${PKG_NAME}
Version: ${VERSION}
Section: education
Priority: optional
Architecture: ${ARCH}
Depends: python3 (>= 3.11), python3-pip, python3-venv, nodejs (>= 20), npm, postgresql (>= 16), redis-server (>= 7), tmux
Maintainer: 42-training <contact@42lausanne.ch>
Description: 42 Lausanne learning platform
 Triple-track learning system (Shell, C, Python+AI) with agentic
 mentor architecture, defense sessions, and terminal integration.
Homepage: https://github.com/decarvalhoe/42-training
EOF

# --- Post-install script ---
cat > "$BUILD_DIR/DEBIAN/postinst" <<'POSTINST'
#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/42-training"
CONF_DIR="/etc/42-training"

# Create system user
if ! id -u training >/dev/null 2>&1; then
    useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin training
fi

# Python virtualenvs
for svc in api ai_gateway; do
    python3 -m venv "$APP_DIR/services/$svc/.venv"
    "$APP_DIR/services/$svc/.venv/bin/pip" install --quiet -r "$APP_DIR/services/$svc/requirements.txt"
done

# Node dependencies
cd "$APP_DIR/apps/web"
npm ci --production --quiet 2>/dev/null || npm install --production --quiet

# Generate default config if missing
if [ ! -f "$CONF_DIR/env" ]; then
    cat > "$CONF_DIR/env" <<ENVFILE
DATABASE_URL=postgresql+asyncpg://training:training@localhost:5432/training
REDIS_URL=redis://localhost:6379/0
API_PORT=8000
AI_GATEWAY_PORT=8100
AI_GATEWAY_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_AI_GATEWAY_URL=http://localhost:8100
PORT=3000
APP_SECRET_KEY=$(openssl rand -hex 32)
ENVFILE
    chmod 600 "$CONF_DIR/env"
    chown training:training "$CONF_DIR/env"
fi

chown -R training:training "$APP_DIR"

# Enable and start services
systemctl daemon-reload
for unit in 42-training-api 42-training-gateway 42-training-web; do
    systemctl enable "$unit.service" || true
done

echo "42-training installed. Start with: systemctl start 42-training-api"
POSTINST
chmod 755 "$BUILD_DIR/DEBIAN/postinst"

# --- Pre-removal script ---
cat > "$BUILD_DIR/DEBIAN/prerm" <<'PRERM'
#!/usr/bin/env bash
set -euo pipefail
for unit in 42-training-web 42-training-gateway 42-training-api; do
    systemctl stop "$unit.service" 2>/dev/null || true
    systemctl disable "$unit.service" 2>/dev/null || true
done
PRERM
chmod 755 "$BUILD_DIR/DEBIAN/prerm"

# --- Systemd units ---
cat > "$BUILD_DIR/usr/lib/systemd/system/42-training-api.service" <<'UNIT'
[Unit]
Description=42-training API server
After=network.target postgresql.service redis-server.service
Requires=postgresql.service redis-server.service

[Service]
Type=simple
User=training
Group=training
WorkingDirectory=/opt/42-training/services/api
EnvironmentFile=/etc/42-training/env
ExecStart=/opt/42-training/services/api/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

cat > "$BUILD_DIR/usr/lib/systemd/system/42-training-gateway.service" <<'UNIT'
[Unit]
Description=42-training AI gateway
After=network.target 42-training-api.service
Requires=42-training-api.service

[Service]
Type=simple
User=training
Group=training
WorkingDirectory=/opt/42-training/services/ai_gateway
EnvironmentFile=/etc/42-training/env
ExecStart=/opt/42-training/services/ai_gateway/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8100
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

cat > "$BUILD_DIR/usr/lib/systemd/system/42-training-web.service" <<'UNIT'
[Unit]
Description=42-training web frontend
After=network.target 42-training-api.service 42-training-gateway.service

[Service]
Type=simple
User=training
Group=training
WorkingDirectory=/opt/42-training/apps/web
EnvironmentFile=/etc/42-training/env
ExecStart=/usr/bin/npm run start
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

# --- CLI wrapper ---
cat > "$BUILD_DIR/usr/bin/42-training" <<'CLI'
#!/usr/bin/env bash
# 42-training CLI wrapper
set -euo pipefail

APP_DIR="/opt/42-training"
CONF="/etc/42-training/env"

usage() {
    echo "Usage: 42-training {start|stop|status|doctor|logs}"
    exit 1
}

case "${1:-}" in
    start)
        sudo systemctl start 42-training-api 42-training-gateway 42-training-web
        echo "All services started."
        ;;
    stop)
        sudo systemctl stop 42-training-web 42-training-gateway 42-training-api
        echo "All services stopped."
        ;;
    status)
        for svc in 42-training-api 42-training-gateway 42-training-web; do
            status=$(systemctl is-active "$svc" 2>/dev/null || echo "inactive")
            printf "%-28s %s\n" "$svc" "$status"
        done
        ;;
    doctor)
        "$APP_DIR/scripts/doctor.sh"
        ;;
    logs)
        journalctl -u "42-training-*" --no-pager -n 50
        ;;
    *)
        usage
        ;;
esac
CLI
chmod 755 "$BUILD_DIR/usr/bin/42-training"

# --- Copy application files ---
cp -r "$REPO_ROOT/services/api/app" "$BUILD_DIR/opt/42-training/services/api/"
cp -r "$REPO_ROOT/services/api/alembic" "$BUILD_DIR/opt/42-training/services/api/"
cp "$REPO_ROOT/services/api/alembic.ini" "$BUILD_DIR/opt/42-training/services/api/"
cp "$REPO_ROOT/services/api/requirements.txt" "$BUILD_DIR/opt/42-training/services/api/"

cp -r "$REPO_ROOT/services/ai_gateway/app" "$BUILD_DIR/opt/42-training/services/ai_gateway/"
cp "$REPO_ROOT/services/ai_gateway/requirements.txt" "$BUILD_DIR/opt/42-training/services/ai_gateway/"

# Web: copy source for build (production build happens in postinst or pre-built)
cp -r "$REPO_ROOT/apps/web/app" "$BUILD_DIR/opt/42-training/apps/web/"
cp -r "$REPO_ROOT/apps/web/lib" "$BUILD_DIR/opt/42-training/apps/web/"
cp -r "$REPO_ROOT/apps/web/public" "$BUILD_DIR/opt/42-training/apps/web/" 2>/dev/null || true
cp -r "$REPO_ROOT/apps/web/services" "$BUILD_DIR/opt/42-training/apps/web/"
cp "$REPO_ROOT/apps/web/package.json" "$BUILD_DIR/opt/42-training/apps/web/"
cp "$REPO_ROOT/apps/web/package-lock.json" "$BUILD_DIR/opt/42-training/apps/web/" 2>/dev/null || true
cp "$REPO_ROOT/apps/web/tsconfig.json" "$BUILD_DIR/opt/42-training/apps/web/"
cp "$REPO_ROOT/apps/web/next.config.ts" "$BUILD_DIR/opt/42-training/apps/web/"

# Curriculum data
cp "$REPO_ROOT/packages/curriculum/data/"*.json "$BUILD_DIR/opt/42-training/packages/curriculum/data/"

# Scripts
for script in doctor.sh smoke_mvp.sh start_api.sh start_ai_gateway.sh start_web.sh; do
    if [ -f "$REPO_ROOT/scripts/$script" ]; then
        cp "$REPO_ROOT/scripts/$script" "$BUILD_DIR/opt/42-training/scripts/"
    fi
done

# Progression template
cp "$REPO_ROOT/progression.json" "$BUILD_DIR/opt/42-training/"

# --- Build the .deb ---
dpkg-deb --build "$BUILD_DIR"
mv "$BUILD_DIR.deb" "$REPO_ROOT/packaging/deb/"

echo "==> Built: packaging/deb/${PKG_NAME}_${VERSION}_${ARCH}.deb"

# Cleanup
rm -rf "$REPO_ROOT/packaging/deb/_build"
