@echo off
chcp 65001 >nul
title Alliance Pioneer

echo.
echo ========================================
echo   Alliance Pioneer - Starting
echo ========================================
echo.

cd /d "%~dp0\..\.."

REM Check port
echo [1/2] Checking port...
netstat -ano | findstr ":8000.*LISTENING" >nul
if not errorlevel 1 (
    echo   Port 8000 in use, killing...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
)
echo   Port ready

echo.
echo [2/2] Starting backend...
echo.
echo ========================================
echo   URL:  http://localhost:8000/
echo   Docs: http://localhost:8000/docs
echo ========================================
echo.

echo   Starting...
echo.

start "" http://localhost:8000/

python -m uvicorn backend.main_fast:app --host 0.0.0.0 --port 8000

pause
