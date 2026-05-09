@echo off
echo ============================================================
echo  LexAI -- Legal Intelligence Platform
echo ============================================================
echo.
echo  Starting FastAPI backend (frontend included at http://localhost:8000)
echo.
echo  Open your browser at: http://localhost:8000
echo  API docs available at: http://localhost:8000/docs
echo ============================================================
echo.
cd /d "%~dp0"
uvicorn backend.main:app --host 0.0.0.0 --port 8000
