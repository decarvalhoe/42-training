<#
.SYNOPSIS
    Build Windows distributables (.exe) for 42 Training.

.DESCRIPTION
    1. Builds the Next.js frontend in standalone mode.
    2. Creates Python virtualenvs for the bundled API and AI Gateway.
    3. Stages frontend, backend and data assets under desktop/.
    4. Runs electron-builder to produce an NSIS installer and portable .exe.
    Outputs land in desktop/dist/.

.PREREQUISITES
    - Node.js >= 20
    - npm
    - Python 3.13
#>

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DesktopDir = Join-Path $RepoRoot "desktop"
$StageDir = Join-Path $DesktopDir "staging"
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue)?.Source

if (-not $PythonExe) {
    Write-Error "python is required on PATH to build the bundled desktop services."
    exit 1
}

Write-Host "=== 42 Training Windows Build ===" -ForegroundColor Cyan
Write-Host "Root:    $RepoRoot"
Write-Host "Python:  $(& $PythonExe --version)"
Write-Host "Node:    $(node --version)"

# ---- Step 1: Clean previous staging ----
Write-Host "`n[1/6] Cleaning staging directory..." -ForegroundColor Yellow
if (Test-Path $StageDir) {
    Remove-Item $StageDir -Recurse -Force
}
New-Item -ItemType Directory -Force `
    -Path (Join-Path $StageDir "backend/api"),
          (Join-Path $StageDir "backend/ai_gateway"),
          (Join-Path $StageDir "frontend"),
          (Join-Path $StageDir "data") | Out-Null

# ---- Step 2: Build Next.js standalone ----
Write-Host "`n[2/6] Building Next.js standalone..." -ForegroundColor Yellow
Push-Location "$RepoRoot\apps\web"
npm ci
npm run build
Pop-Location

if (-not (Test-Path "$RepoRoot\apps\web\.next\standalone")) {
    Write-Error "Standalone build not found. Ensure next.config.mjs has output: 'standalone'."
    exit 1
}

Write-Host "  Next.js standalone build OK" -ForegroundColor Green

# Copy standalone output into the desktop staging area
Copy-Item "$RepoRoot\apps\web\.next\standalone\*" (Join-Path $StageDir "frontend") -Recurse -Force
New-Item -ItemType Directory -Force -Path (Join-Path $StageDir "frontend\.next") | Out-Null
Copy-Item "$RepoRoot\apps\web\.next\static" (Join-Path $StageDir "frontend\.next") -Recurse -Force
if (Test-Path "$RepoRoot\apps\web\public") {
    Copy-Item "$RepoRoot\apps\web\public" (Join-Path $StageDir "frontend") -Recurse -Force
}

# ---- Step 3: Create Python virtualenvs ----
Write-Host "`n[3/6] Creating Python virtualenvs..." -ForegroundColor Yellow
foreach ($svc in @("api", "ai_gateway")) {
    $srcDir = Join-Path $RepoRoot "services\$svc"
    $dstDir = Join-Path $StageDir "backend\$svc"

    & $PythonExe -m venv "$dstDir\venv"
    & "$dstDir\venv\Scripts\python.exe" -m pip install --upgrade pip
    & "$dstDir\venv\Scripts\pip.exe" install -r "$srcDir\requirements.txt"

    Copy-Item "$srcDir\app" $dstDir -Recurse -Force
    Copy-Item "$srcDir\requirements.txt" $dstDir -Force

    if (Test-Path "$srcDir\alembic") {
        Copy-Item "$srcDir\alembic" $dstDir -Recurse -Force
    }
    if (Test-Path "$srcDir\alembic.ini") {
        Copy-Item "$srcDir\alembic.ini" $dstDir -Force
    }
}

Write-Host "  Python services staged OK" -ForegroundColor Green

# ---- Step 4: Copy shared data ----
Write-Host "`n[4/6] Copying shared data..." -ForegroundColor Yellow
Copy-Item "$RepoRoot\packages\curriculum\data\42_lausanne_curriculum.json" (Join-Path $StageDir "data") -Force
Copy-Item "$RepoRoot\progression.json" (Join-Path $StageDir "data") -Force

# ---- Step 5: Assemble desktop app ----
Write-Host "`n[5/6] Assembling Electron app..." -ForegroundColor Yellow
Remove-Item "$DesktopDir\backend", "$DesktopDir\frontend", "$DesktopDir\data" -Recurse -Force -ErrorAction SilentlyContinue
Move-Item (Join-Path $StageDir "backend") "$DesktopDir\backend"
Move-Item (Join-Path $StageDir "frontend") "$DesktopDir\frontend"
Move-Item (Join-Path $StageDir "data") "$DesktopDir\data"
Remove-Item $StageDir -Recurse -Force

Push-Location $DesktopDir
npm ci
Pop-Location

Write-Host "  Electron deps OK" -ForegroundColor Green

# ---- Step 6: Build Electron distributable ----
Write-Host "`n[6/6] Building Windows distributable..." -ForegroundColor Yellow
Push-Location $DesktopDir
npm run dist:win
Pop-Location

Write-Host "`n=== Build complete ===" -ForegroundColor Cyan
Write-Host "Output: desktop\dist\" -ForegroundColor Green
Write-Host "  - NSIS installer (.exe)"
Write-Host "  - Portable (.exe)"
