@echo off
REM ===============================================
REM Build run.exe cho EAUT bang PyInstaller
REM Yeu cau: Python 3.10+ tren may build
REM ===============================================
setlocal
cd /d "%~dp0"

echo.
echo === [1/5] Kiem tra Python + dependencies ===
python --version
if errorlevel 1 (
    echo [LOI] Khong tim thay python trong PATH.
    echo Cai Python tu https://python.org va them vao PATH.
    pause
    exit /b 1
)

echo.
echo === [2/5] Install requirements + PyInstaller ===
pip install --quiet -r requirements.txt
pip install --quiet pyinstaller
if errorlevel 1 (
    echo [LOI] Khong cai duoc dependencies.
    pause
    exit /b 1
)

echo.
echo === [3/5] Tat run.exe cu (neu dang chay) + cleanup file lock ===
taskkill /IM run.exe /F >nul 2>&1
taskkill /IM uvicorn.exe /F >nul 2>&1
REM doi 2s cho OS release file handle
ping -n 3 127.0.0.1 >nul

echo.
echo === [4/5] Don dep build cu ===
if exist build rmdir /s /q build 2>nul
if exist dist (
    rmdir /s /q dist 2>nul
    REM neu rmdir fail vi file lock, thu xoa run.exe rieng le
    if exist dist\run.exe (
        del /f /q dist\run.exe 2>nul
        if exist dist\run.exe (
            echo [CANH BAO] Khong xoa duoc dist\run.exe - dang co process khac dung.
            echo Hay tat het run.exe trong Task Manager roi chay lai script nay.
            pause
            exit /b 1
        )
    )
)

echo.
echo === [5/5] Build run.exe (mat 2-5 phut) ===
pyinstaller --clean --noconfirm run.spec
if errorlevel 1 (
    echo.
    echo [LOI] PyInstaller build that bai - exit code %errorlevel%.
    echo.
    echo Cac nguyen nhan thuong gap:
    echo   1. dist\run.exe dang chay - tat trong Task Manager
    echo   2. Antivirus block - tam thoi tat AV roi build lai
    echo   3. Disk full - check dung luong o E:\
    pause
    exit /b 1
)

echo.
echo ===============================================
echo  BUILD XONG!
echo  File: dist\run.exe
echo  Kich thuoc:
dir dist\run.exe | findstr "run.exe"
echo ===============================================
echo.
echo De chay: double-click dist\run.exe
echo Yeu cau may dich: Docker Desktop dang chay
echo.
pause
