@echo off
echo ===================================================
echo   Starting CodeIntel (Backend + Frontend)
echo ===================================================

echo [1/2] Launching Backend FastAPI Server...
start "CodeIntel Backend (FastAPI)" cmd /k "cd /d "%~dp0backend" && if exist .venv\Scripts\activate.bat (call .venv\Scripts\activate.bat) && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo [2/2] Launching Frontend Vite Server...
start "CodeIntel Frontend (Vite)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo All services launched!
echo   * Frontend: http://localhost:5173
echo   * Backend:  http://127.0.0.1:8000
echo   * API Docs: http://127.0.0.1:8000/docs
echo ===================================================
