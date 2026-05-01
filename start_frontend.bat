@echo off
REM ===============================================
REM Khoi dong frontend EAUT (PyQt5 UI)
REM Yeu cau: backend dang chay (start_backend.bat)
REM ===============================================
setlocal
cd /d "%~dp0"

REM Kiem tra API truoc
curl -s -m 3 http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo [CANH BAO] Backend chua chay tai http://localhost:8000
    echo Hay chay 'start_backend.bat' truoc trong cua so khac.
    echo.
    set /p ans="Van muon mo frontend? (y/N): "
    if /i not "%ans%"=="y" exit /b 1
)

python frontend\main.py
