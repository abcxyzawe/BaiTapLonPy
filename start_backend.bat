@echo off
REM ===============================================
REM Khoi dong backend EAUT (PostgreSQL + REST API)
REM Chay 1 lan, mo cmd window de logs
REM ===============================================
setlocal
cd /d "%~dp0"

echo.
echo === [1/3] Kiem tra Docker ===
docker info >nul 2>&1
if errorlevel 1 (
    echo [LOI] Docker chua chay. Mo Docker Desktop truoc.
    pause
    exit /b 1
)

echo.
echo === [2/3] Start PostgreSQL container ===
docker compose up -d postgres
if errorlevel 1 (
    echo [LOI] Khong start duoc postgres container.
    pause
    exit /b 1
)

echo Doi DB san sang...
:wait_db
docker exec eaut_postgres pg_isready -U eaut_admin -d eaut_db >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_db
)
echo PostgreSQL ready: localhost:5432

echo.
echo === [3/3] Start REST API server (uvicorn :8000) ===
echo.
echo  API docs: http://localhost:8000/docs
echo  Health:   http://localhost:8000/health
echo.
echo  Nhan Ctrl+C de tat API server.
echo  Postgres van chay nen sau khi tat API.
echo.

REM --reload-dir backend: chi watch backend/ - khong restart khi sua frontend/
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend
