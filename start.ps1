# XFeat Vision Lab — Start Script
# Run this from PowerShell: powershell -ExecutionPolicy Bypass -File start.ps1

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir  = Join-Path $ProjectDir "backend"
$IndexFile   = Join-Path $ProjectDir "frontend\index.html"

Write-Host ""
Write-Host "XFeat Vision Lab" -ForegroundColor Cyan
Write-Host "Backend  -> http://localhost:5000" -ForegroundColor DarkCyan
Write-Host "Frontend -> Open frontend\index.html in your browser" -ForegroundColor DarkCyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor DarkGray
Write-Host ""

# Open browser after 4 seconds (non-blocking)
$null = Start-Process powershell -ArgumentList "-WindowStyle Hidden -Command Start-Sleep 4; Start-Process '$IndexFile'" -WindowStyle Hidden

# Start Flask backend (blocking — keep this window open)
Set-Location $BackendDir
python app.py
