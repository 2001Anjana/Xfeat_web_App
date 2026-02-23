# ════════════════════════════════════════════
#  XFeat Vision Lab — One-time Setup Script
#  Run this ONCE before first launch
# ════════════════════════════════════════════

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ProjectDir "backend"

Write-Host ""
Write-Host "XFeat Vision Lab - Setup" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor DarkCyan

# 1. Clone XFeat repo into backend/
$xfeatDir = Join-Path $BackendDir "accelerated_features"
if (-Not (Test-Path $xfeatDir)) {
    Write-Host ""
    Write-Host "[1/3] Cloning XFeat repository..." -ForegroundColor Yellow
    git clone https://github.com/verlab/accelerated_features.git $xfeatDir
} else {
    Write-Host ""
    Write-Host "[1/3] XFeat repo already present. Skipping clone." -ForegroundColor Green
}

# 2. Install Python dependencies
Write-Host ""
Write-Host "[2/3] Installing Python dependencies..." -ForegroundColor Yellow
Set-Location $BackendDir
pip install -r requirements.txt

Write-Host ""
Write-Host "[3/3] Setup complete!" -ForegroundColor Green
Write-Host "Now run start.ps1 to launch the application." -ForegroundColor Cyan
