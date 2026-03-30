#!/usr/bin/env bash
# Build an RPM package for 42-training (Fedora/RHEL/CentOS).
# Requires: rpmbuild, rpmdevtools
# Usage: ./packaging/rpm/build-rpm.sh [version]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="${1:-0.1.0}"
PKG_NAME="42-training"

echo "==> Building ${PKG_NAME}-${VERSION}.rpm"

# Setup rpmbuild tree
rpmdev-setuptree 2>/dev/null || mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Create source tarball
TARBALL_DIR=$(mktemp -d)
mkdir -p "$TARBALL_DIR/${PKG_NAME}-${VERSION}"
rsync -a --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
    --exclude='.next' --exclude='.venv' --exclude='*.pyc' \
    "$REPO_ROOT/" "$TARBALL_DIR/${PKG_NAME}-${VERSION}/"

tar czf ~/rpmbuild/SOURCES/${PKG_NAME}-${VERSION}.tar.gz \
    -C "$TARBALL_DIR" "${PKG_NAME}-${VERSION}"
rm -rf "$TARBALL_DIR"

# Copy systemd units alongside spec
for svc in api gateway web; do
    cp "$REPO_ROOT/packaging/deb/build-deb.sh" /dev/null 2>/dev/null || true
done

# Copy spec
cp "$REPO_ROOT/packaging/rpm/42-training.spec" ~/rpmbuild/SPECS/
sed -i "s/^Version:.*/Version:        ${VERSION}/" ~/rpmbuild/SPECS/42-training.spec

# Build
rpmbuild -bb ~/rpmbuild/SPECS/42-training.spec

echo "==> RPM built in ~/rpmbuild/RPMS/"
