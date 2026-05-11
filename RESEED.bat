@echo off
REM =====================================================
REM Script tu dong Reset va Seed Database cho EAUT
REM =====================================================
title EAUT - Reset Database
cd /d "%~dp0"

echo.
echo ============================================================
echo           EAUT - TU DONG KHOI TAO LAI DATABASE
echo ============================================================
echo.

REM --- Kiem tra Docker ---
docker info >nul 2>&1
if errorlevel 1 (
    echo [LOI] Docker Desktop chua chay!
    pause
    exit /b 1
)

REM --- Kiem tra Container ---
docker inspect eaut_postgres >nul 2>&1
if errorlevel 1 (
    echo [THONG BAO] Container eaut_postgres chua ton tai. Dang khoi chay...
    docker compose up -d postgres
    timeout /t 5 >nul
)

echo [1/2] Dang thuc thi schema.sql (Xoa va tao lai cac bang)...
docker exec -i eaut_postgres psql -U eaut_admin -d eaut_db < database\schema.sql
if errorlevel 1 (
    REM Fallback neu schema.sql nam trong backend/database
    docker exec -i eaut_postgres psql -U eaut_admin -d eaut_db < backend\database\schema.sql
)

echo [2/2] Dang thuc thi seed.sql (Nap du lieu mau)...
docker exec -i eaut_postgres psql -U eaut_admin -d eaut_db < database\seed.sql
if errorlevel 1 (
    REM Fallback neu seed.sql nam trong backend/database
    docker exec -i eaut_postgres psql -U eaut_admin -d eaut_db < backend\database\seed.sql
)

echo.
echo ============================================================
echo [THANH CONG] Database da duoc lam moi hoan toan!
echo ============================================================
echo.
pause
