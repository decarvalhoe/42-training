<#
.SYNOPSIS
    Build a Windows distributable (.exe / .msi) for 42 Training.

.DESCRIPTION
    1. Builds the Next.js frontend in standalone mode.
    2. Runs electron-builder to produce an NSIS installer and portable .exe.
    Outputs land in desktop/dist/.

.PREREQUISITES
    - Node.js >= 20
    - npm
    - Python 3.13 (for backend services — not bundled)
    - Docker Desktop (recommended for running backend services)
#>

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "=== 42 Training Windows Build ===" -ForegroundColor Cyan

# ---- Step 1: Build Next.js standalone ----
Write-Host "`n[1/3] Building Next.js standalone..." -ForegroundColor Yellow
Push-Location "$RepoRoot\apps\web"
npm ci
npm run build
Pop-Location

if (-not (Test-Path "$RepoRoot\apps\web\.next\standalone")) {
    Write-Error "Standalone build not found. Ensure next.config.mjs has output: 'standalone'."
    exit 1
}

Write-Host "  Next.js standalone build OK" -ForegroundColor Green

# ---- Step 2: Install Electron deps ----
Write-Host "`n[2/3] Installing Electron dependencies..." -ForegroundColor Yellow
Push-Location "$RepoRoot\desktop"
npm ci
Pop-Location

Write-Host "  Electron deps OK" -ForegroundColor Green

# ---- Step 3: Build Electron distributable ----
Write-Host "`n[3/3] Building Windows distributable..." -ForegroundColor Yellow
Push-Location "$RepoRoot\desktop"
npx electron-builder --win
Pop-Location

Write-Host "`n=== Build complete ===" -ForegroundColor Cyan
Write-Host "Output: desktop\dist\" -ForegroundColor Green
Write-Host "  - NSIS installer (.exe)"
Write-Host "  - Portable (.exe)"
