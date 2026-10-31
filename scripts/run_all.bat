@echo off
echo ============================================================
echo   NEXUS AI FINOPS - Dual Service Launcher
echo ============================================================
start "NEXUS AI FINOPS Backend" cmd /c "%~dp0run_backend.bat"
start "NEXUS AI FINOPS Frontend" cmd /c "%~dp0run_frontend.bat"
echo Services launched!
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://localhost:5173
pause

