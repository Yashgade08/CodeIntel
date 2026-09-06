# CodeIntel One-Click Launcher for PowerShell
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "   Starting CodeIntel (Backend + Frontend)" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

$backendPath = Join-Path $PSScriptRoot "backend"
$frontendPath = Join-Path $PSScriptRoot "frontend"

Write-Host "[1/2] Launching Backend FastAPI Server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$backendPath'; if (Test-Path '.\.venv\Scripts\Activate.ps1') { .\.venv\Scripts\Activate.ps1 }; uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

Write-Host "[2/2] Launching Frontend Vite Server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$frontendPath'; npm run dev"

Write-Host ""
Write-Host "All services launched!" -ForegroundColor Green
Write-Host "  * Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host "  * Backend:  http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "  * API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Cyan
