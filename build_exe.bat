@echo off
REM ===============================================
REM Build run.exe cho EAUT bang PyInstaller
REM Yeu cau: Python 3.10+ tren may build
REM ===============================================
setlocal
cd /d "%~dp0"

echo.
echo === [1/4] Kiem tra Python + dependencies ===
python --version
if errorlevel 1 (
    echo [LOI] Khong tim thay python trong PATH.
    echo Cai Python tu https://python.org va them vao PATH.
    pause
    exit /b 1
)

echo.
echo === [2/4] Install requirements + PyInstaller ===
pip install --quiet -r requirements.txt
pip install --quiet pyinstaller
if errorlevel 1 (
    echo [LOI] Khong cai duoc dependencies.
    pause
    exit /b 1
)

echo.
echo === [3/4] Don dep build cu ===
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo === [4/4] Build run.exe (mat 2-5 phut) ===
pyinstaller --clean --noconfirm run.spec
if errorlevel 1 (
    echo [LOI] Build that bai.
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
