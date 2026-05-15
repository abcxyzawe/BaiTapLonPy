@echo off
REM =====================================================
REM EAUT - 1-click launcher
REM Khoi dong toan bo: Docker + DB + API + UI
REM Dung: double-click file nay
REM =====================================================
title EAUT - Khoi dong he thong
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1

echo.
echo ============================================================
echo                EAUT - HE THONG DANG KY KHOA HOC
echo ============================================================
echo.

REM === [1/5] Don dep tien trinh cu ===
echo [1/5] Don dep tien trinh cu (uvicorn dang giu port 8000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo    OK
echo.

REM === [2/5] Xoa cache cu ===
echo [2/5] Xoa cache Python cu (de chac an code moi duoc load)...
if exist frontend\__pycache__ rmdir /s /q frontend\__pycache__ >nul 2>&1
for /d /r backend %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" >nul 2>&1
echo    OK
echo.

REM === [3/5] Kiem tra Docker + Start PostgreSQL ===
echo [3/5] Kiem tra Docker...
docker info >nul 2>&1
if errorlevel 1 (
    echo    [LOI] Docker chua chay! Mo Docker Desktop truoc roi chay lai.
    echo.
    pause
    exit /b 1
)
echo    Docker OK
echo    Khoi dong PostgreSQL container...
docker compose up -d postgres
if errorlevel 1 (
    echo    [LOI] Khong start duoc PostgreSQL container.
    pause
    exit /b 1
)
echo    Doi DB san sang...
:wait_db
docker exec eaut_postgres pg_isready -U eaut_admin -d eaut_db >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_db
)
echo    PostgreSQL ready: localhost:5433
echo.

REM === [4/5] Khoi dong backend (cua so rieng) ===
echo [4/5] Khoi dong REST API server (uvicorn :8000)...
start "EAUT Backend" /min cmd /k "title EAUT Backend && cd /d %~dp0 && python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir backend"

echo    Doi backend san sang...
set /a count=0
:wait_api
curl -s -m 2 http://127.0.0.1:8000/health >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    set /a count+=1
    if !count! geq 30 (
        echo    [LOI] Backend khong phan hoi sau 30s. Kiem tra cua so EAUT Backend.
        pause
        exit /b 1
    )
    goto wait_api
)
echo    Backend ready: http://127.0.0.1:8000
echo.

REM === [5/5] Khoi dong frontend ===
echo [5/5] Khoi dong giao dien PyQt5...
echo.
echo ============================================================
echo  Tat app: dong cua so PyQt
echo  Backend van chay o cua so "EAUT Backend" (minimized)
echo  Khi muon tat het: chay STOP.bat
echo ============================================================
echo.

cd frontend
python main.py
cd ..

REM === Sau khi UI dong, hoi co dong backend khong ===
echo.
echo Frontend da dong.
choice /C YN /M "Tat luon backend (Y/N)"
if errorlevel 2 goto :end
echo Dang tat backend...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo Backend da tat.

:end
echo.
echo Hen gap lai!
timeout /t 3 /nobreak >nul
