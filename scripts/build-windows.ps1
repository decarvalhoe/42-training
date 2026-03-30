<#
.SYNOPSIS
    Build a Windows distributable (.exe / .msi) for 42 Training.

.DESCRIPTION
    1. Builds the Next.js frontend in standalone mode.
    2. Stages the standalone bundle into desktop/frontend.
    3. Runs electron-builder to produce an NSIS installer and portable .exe.
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
Write-Host "`n[1/4] Building Next.js standalone..." -ForegroundColor Yellow
Push-Location "$RepoRoot\apps\web"
npm install
if ($LASTEXITCODE -ne 0) { throw "npm install failed in apps/web" }
npm run build
if ($LASTEXITCODE -ne 0) { throw "npm run build failed in apps/web" }
Pop-Location

if (-not (Test-Path "$RepoRoot\apps\web\.next\standalone")) {
    Write-Error "Standalone build not found. Ensure next.config.mjs has output: 'standalone'."
    exit 1
}

Write-Host "  Next.js standalone build OK" -ForegroundColor Green

# ---- Step 2: Stage frontend bundle for Electron ----
Write-Host "`n[2/4] Staging frontend bundle..." -ForegroundColor Yellow
$DesktopFrontend = Join-Path $RepoRoot "desktop\frontend"
Remove-Item -LiteralPath $DesktopFrontend -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $DesktopFrontend | Out-Null

Copy-Item -Path "$RepoRoot\apps\web\.next\standalone\*" -Destination $DesktopFrontend -Recurse -Force
New-Item -ItemType Directory -Path "$DesktopFrontend\.next" -Force | Out-Null
Copy-Item -Path "$RepoRoot\apps\web\.next\static" -Destination "$DesktopFrontend\.next" -Recurse -Force

if (Test-Path "$RepoRoot\apps\web\public") {
    Copy-Item -Path "$RepoRoot\apps\web\public" -Destination $DesktopFrontend -Recurse -Force
}

Write-Host "  Frontend bundle staged to desktop\frontend" -ForegroundColor Green

# ---- Step 3: Install Electron deps ----
Write-Host "`n[3/4] Installing Electron dependencies..." -ForegroundColor Yellow
Push-Location "$RepoRoot\desktop"
npm ci
if ($LASTEXITCODE -ne 0) { throw "npm ci failed in desktop" }
Pop-Location

Write-Host "  Electron deps OK" -ForegroundColor Green

# ---- Step 4: Build Electron distributable ----
Write-Host "`n[4/4] Building Windows distributable..." -ForegroundColor Yellow
Push-Location "$RepoRoot\desktop"
npx electron-builder --win
if ($LASTEXITCODE -ne 0) { throw "electron-builder --win failed" }
Pop-Location

Write-Host "`n=== Build complete ===" -ForegroundColor Cyan
Write-Host "Output: desktop\dist\" -ForegroundColor Green
Write-Host "  - NSIS installer (.exe)"
Write-Host "  - Portable (.exe)"
