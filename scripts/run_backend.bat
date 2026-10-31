@echo off
echo Starting NEXUS AI FINOPS Backend on http://127.0.0.1:8000...
cd /d "%~dp0\..\backend"
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
pause

