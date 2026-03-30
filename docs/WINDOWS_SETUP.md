# Windows Setup — 42 Training Desktop

## Overview

The 42 Training desktop app packages the Next.js frontend as a native Windows
application via Electron. Backend services (API + AI Gateway) run separately,
either through Docker Desktop or manual Python setup.

## Architecture

```
┌──────────────────────────────────┐
│   42 Training (.exe)             │
│   ┌────────────────────────────┐ │
│   │  Electron shell            │ │
│   │  ┌──────────────────────┐  │ │
│   │  │ Next.js standalone   │  │ │
│   │  │ (port 3042)          │  │ │
│   │  └──────────────────────┘  │ │
│   └────────────────────────────┘ │
└──────────┬───────────────────────┘
           │ HTTP
┌──────────▼───────────────────────┐
│  Backend (Docker Desktop)        │
│  ├─ API (port 8000)             │
│  ├─ AI Gateway (port 8100)      │
│  ├─ PostgreSQL (port 5432)      │
│  └─ Redis (port 6379)           │
└──────────────────────────────────┘
```

## Prerequisites

| Requirement        | Version   | Purpose                     |
|--------------------|-----------|-----------------------------|
| Windows            | 10+ x64   | Target platform             |
| Node.js            | >= 20     | Build + Next.js runtime     |
| Docker Desktop     | >= 4.0    | Backend services            |
| Git                | >= 2.40   | Clone repository            |
| Python (optional)  | 3.13      | Run backends without Docker |

## Quick Start (Docker backends)

```powershell
# 1. Clone and enter the repository
git clone https://github.com/decarvalhoe/42-training.git
cd 42-training

# 2. Start backend services via Docker
docker compose up -d api ai_gateway

# 3. Run the desktop app in development mode
cd desktop
npm install
npm start
```

## Building the Installer

```powershell
# From the repository root
.\scripts\build-windows.ps1
```

This produces two artifacts in `desktop\dist\`:
- **NSIS installer** — standard Windows setup wizard (.exe)
- **Portable** — single-file executable, no installation required

## Manual Backend Setup (without Docker)

If Docker Desktop is not available, run the backends manually:

```powershell
# Terminal 1 — API
cd services\api
pip install -r requirements.txt
$env:DATABASE_URL = "sqlite+aiosqlite:///training.db"
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — AI Gateway
cd services\ai_gateway
pip install -r requirements.txt
$env:AI_GATEWAY_API_BASE_URL = "http://localhost:8000"
uvicorn app.main:app --host 127.0.0.1 --port 8100
```

## Environment Variables

| Variable                        | Default                  | Description              |
|---------------------------------|--------------------------|--------------------------|
| `PORT`                          | `3042`                   | Frontend port            |
| `NEXT_PUBLIC_API_URL`           | `http://localhost:8000`  | Backend API URL          |
| `NEXT_PUBLIC_AI_GATEWAY_URL`    | `http://localhost:8100`  | AI Gateway URL           |
| `DATABASE_URL`                  | PostgreSQL connection    | API database             |

## CI/CD

The `build-windows.yml` workflow runs on:
- Git tags matching `v*` (releases)
- Manual dispatch (`workflow_dispatch`)

Artifacts are uploaded to the Actions run and retained for 30 days.

## Troubleshooting

**"Server Error" on startup**
The desktop app starts a Next.js server internally. If it fails, ensure the
build was run with `output: "standalone"` in `next.config.mjs`.

**Backend unreachable**
The frontend defaults to `http://localhost:8000` for the API. Start backends
via `docker compose up -d` or the manual setup above before launching the app.

**Build fails on electron-builder**
Ensure you are running the build on a Windows machine or in a Windows CI
runner. Cross-compilation from Linux is not supported for NSIS installers.
