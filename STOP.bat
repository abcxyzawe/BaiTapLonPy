@echo off
REM =====================================================
REM EAUT - Dung tat ca tien trinh
REM =====================================================
title EAUT - Dung he thong
chcp 65001 >nul 2>&1

echo.
echo Dang dung tat ca tien trinh EAUT...
echo.

REM Kill uvicorn (port 8000)
echo [1/3] Tat REST API (port 8000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Kill frontend python (cua so PyQt)
echo [2/3] Tat frontend PyQt5...
taskkill /F /FI "WINDOWTITLE eq EAUT*" >nul 2>&1

REM Stop docker container (postgres van chay phan vung khac)
echo [3/3] Tat PostgreSQL container...
docker compose stop postgres >nul 2>&1

echo.
echo Da tat tat ca.
timeout /t 3 /nobreak >nul
