# Linux Distribution Strategy

## Overview

42-training ships as a multi-service application (API + AI gateway + web frontend) with external dependencies on PostgreSQL and Redis. This document covers native packaging for mainstream Linux distributions and portable formats.

## Package Formats

| Format | Target distros | Install method | Directory | Release status |
|--------|---------------|----------------|-----------|----------------|
| `.deb` | Debian, Ubuntu, Pop!_OS, Mint | `dpkg -i` / `apt install` | `packaging/deb/` | Official release artifact |
| AppImage | Any Linux (portable) | Download and run | `packaging/appimage/` | Official release artifact |
| `.tar.gz` | Custom/minimal distros | Extract and build from source | generated in release workflow | Official release artifact |
| `.rpm` | Fedora, RHEL, CentOS, openSUSE | `rpm -i` / `dnf install` | `packaging/rpm/` | Experimental script, not attached to official releases yet |
| Snap | Ubuntu, any snapd-enabled distro | `snap install` | `packaging/snap/` | Experimental script, not attached to official releases yet |

## Architecture

All packages install to `/opt/42-training/` with:

```
/opt/42-training/
├── services/
│   ├── api/              # FastAPI backend (Python 3.13, uvicorn)
│   └── ai_gateway/       # FastAPI AI orchestration (Python 3.13, uvicorn)
├── apps/
│   └── web/              # Next.js frontend (Node 20)
├── packages/
│   └── curriculum/data/  # Curriculum JSON files
├── scripts/              # Operational scripts
└── progression.json      # Default learner state template
```

### Systemd services

The `.deb` and `.rpm` packages register three systemd units:

| Unit | Port | Depends on |
|------|------|------------|
| `42-training-api.service` | 8000 | PostgreSQL, Redis |
| `42-training-gateway.service` | 8100 | api |
| `42-training-web.service` | 3000 | api, gateway |

Configuration lives in `/etc/42-training/env` (generated on first install with a random `APP_SECRET_KEY`).

### CLI wrapper

All formats provide a `42-training` command:

```bash
42-training start    # Start all services
42-training stop     # Stop all services
42-training status   # Show service status
42-training doctor   # Run diagnostics
42-training logs     # Tail recent logs
```

## Building

### .deb (Debian/Ubuntu)

```bash
# Requires: dpkg-deb
./packaging/deb/build-deb.sh 0.1.0
# Output: packaging/deb/42-training_0.1.0_amd64.deb
```

### .rpm (Fedora/RHEL)

```bash
# Requires: rpmbuild, rpmdevtools
./packaging/rpm/build-rpm.sh 0.1.0
# Output: ~/rpmbuild/RPMS/x86_64/42-training-0.1.0-1.*.rpm
```

This path is still experimental and is not currently published as a release asset.

### AppImage

```bash
# Requires: curl (for appimagetool download)
./packaging/appimage/build-appimage.sh 0.1.0
# Output: AppDir assembled; final .AppImage requires FUSE
```

### Snap

```bash
# Requires: snapcraft
cd packaging/snap
snapcraft
# Output: 42-training_0.1.0_amd64.snap
```

This path is still experimental and is not currently published as a release asset.

## Dependencies

### Runtime (all formats)

| Dependency | Version | Why |
|------------|---------|-----|
| Python 3 | >= 3.11 | API and AI gateway |
| Node.js | >= 20 | Web frontend |
| PostgreSQL | >= 16 | Learner state, progression, sessions |
| Redis | >= 7 | Mentor conversation memory, session cache |
| tmux | any | Terminal integration, agent sessions |

### Build-time

| Tool | Format |
|------|--------|
| `dpkg-deb` | .deb |
| `rpmbuild` + `rpmdevtools` | .rpm |
| `appimagetool` | AppImage (auto-downloaded) |
| `snapcraft` | Snap |

## Post-install steps

1. Ensure PostgreSQL is running with a `training` database:
   ```bash
   sudo -u postgres createuser training
   sudo -u postgres createdb -O training training
   ```

2. Ensure Redis is running:
   ```bash
   sudo systemctl start redis-server  # Debian/Ubuntu
   sudo systemctl start redis         # Fedora/RHEL
   ```

3. Edit configuration if needed:
   ```bash
   sudo nano /etc/42-training/env
   ```

4. Start:
   ```bash
   42-training start
   # or: sudo systemctl start 42-training-api 42-training-gateway 42-training-web
   ```

5. Open http://localhost:3000

## Format decision matrix

| Criterion | .deb | .rpm | AppImage | Snap |
|-----------|------|------|----------|------|
| System integration | Excellent | Excellent | None | Good |
| Auto-updates | via apt | via dnf | Manual | Automatic |
| Sandboxing | None | None | None | Classic confinement |
| Offline install | Yes | Yes | Yes | Yes |
| Custom 42 builds | Best fit | Good | Portable | Store distribution |
| Dependencies handled | postinst | %post | Bundled | Bundled |

**Recommended for 42 campuses:** `.deb` (most campuses run Ubuntu).
**Recommended for portability:** AppImage (zero install, runs anywhere).
**Recommended for custom distros and reproducible local builds:** source `.tar.gz`.
