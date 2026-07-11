@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Alliance Pioneer

echo.
echo ========================================
echo   Alliance Pioneer - Starting
echo ========================================
echo.

cd /d "%~dp0"

REM [0/5] Disable system sleep to prevent idle shutdown
echo [0/5] Disabling system sleep...
powercfg /change standby-timeout-ac 0 >nul 2>&1
powercfg /change standby-timeout-dc 0 >nul 2>&1
powercfg /change hibernate-timeout-ac 0 >nul 2>&1
powercfg /change hibernate-timeout-dc 0 >nul 2>&1
echo   Done - system will not sleep

REM [1/4] Kill existing processes on port 8000
echo [1/4] Checking port 8000...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000.*LISTENING"') do (
    echo   Killing PID %%a...
    taskkill /F /PID %%a >nul 2>&1
)
REM Also kill any lingering python uvicorn processes
taskkill /F /FI "WINDOWTITLE eq Alliance Pioneer" >nul 2>&1

REM Wait for port to be fully released
set WAIT=0
:waitloop
netstat -ano 2>nul | findstr ":8000.*LISTENING" >nul
if not errorlevel 1 (
    set /a WAIT+=1
    if !WAIT! GEQ 10 (
        echo   WARNING: Port 8000 still in use after 10s, forcing...
        for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000.*LISTENING"') do taskkill /F /PID %%a >nul 2>&1
    ) else (
        timeout /t 1 /nobreak >nul
        goto waitloop
    )
)
echo   Port 8000 ready

REM [2/4] Clear all __pycache__ directories (prevent stale bytecode)
echo [2/4] Clearing pycache...
for /d /r %%d in (__pycache__) do (
    if exist "%%d" (
        rd /s /q "%%d" 2>nul
    )
)
echo   Done

REM [3/4] Wait a moment for filesystem to settle
timeout /t 2 /nobreak >nul

REM [4/4] Start backend - try smart starter first, fallback to direct
echo [4/4] Starting backend...
echo.

if not exist "logs" mkdir logs

echo ========================================
echo   URL:  http://localhost:8000/
echo   Docs: http://localhost:8000/docs
echo   Logs: logs\
echo ========================================
echo.

REM Open browser after delay
start "" cmd /c "timeout /t 20 /nobreak >nul && start http://localhost:8000/"

REM Try smart starter with watchfiles-based reload (avoids Windows socketpair issue)
python start_smart.py 2>nul
if errorlevel 1 (
    echo   Smart starter failed, trying direct uvicorn with --reload...
    python -m uvicorn backend.main_fast:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 30 --reload --reload-dir backend --reload-dir core --reload-dir infrastructure --reload-dir config 2>&1 | python -c "import sys,logging; from logging.handlers import TimedRotatingFileHandler; h=TimedRotatingFileHandler('logs/cmd_output.log',when='midnight',backupCount=7,encoding='utf-8'); h.setFormatter(logging.Formatter('%%(asctime)s | %%(message)s')); l=logging.getLogger('cmd'); l.addHandler(h); l.setLevel(logging.INFO); [l.info(line.rstrip()) for line in sys.stdin]" 2>nul
    if errorlevel 1 (
        echo   --reload failed, starting without reload...
        python -m uvicorn backend.main_fast:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 30 2>&1 | python -c "import sys,logging; from logging.handlers import TimedRotatingFileHandler; h=TimedRotatingFileHandler('logs/cmd_output.log',when='midnight',backupCount=7,encoding='utf-8'); h.setFormatter(logging.Formatter('%%(asctime)s | %%(message)s')); l=logging.getLogger('cmd'); l.addHandler(h); l.setLevel(logging.INFO); [l.info(line.rstrip()) for line in sys.stdin]" 2>nul
    )
)

echo.
echo ========================================
echo   Server stopped. Restarting in 5s...
echo ========================================
echo.
timeout /t 5 /nobreak >nul
goto :eof
