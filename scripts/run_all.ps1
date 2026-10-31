Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  NEXUS AI FINOPS - Dual Service Launcher" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$rootDir = Split-Path -Parent $PSScriptRoot

Start-Process -FilePath "python" -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port 8000 --reload" -WorkingDirectory "$rootDir\backend"
Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory "$rootDir\frontend"

Write-Host "Services started:" -ForegroundColor Green
Write-Host "  Backend API:  http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "  Frontend Web: http://localhost:5173" -ForegroundColor Green

