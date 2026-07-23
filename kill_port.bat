@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

REM ==========================================
REM  kill_port.bat — 强制释放端口 8000
REM  用于 start.bat 中端口清理失败时的备用方案
REM  用法: 双击运行，或在端口冲突时手动执行
REM ==========================================

echo [🔍] 正在检测端口 8000 占用情况...

set FOUND=0

REM 方法1: 通过 findstr 找 LISTENING 状态的端口
for /f "skip=4 delims=" %%a in ('netstat -ano ^| findstr ":8000"') do (
    set "LINE=%%a"
    echo   发现: %%a
    
    REM 从行末提取 PID（最后一个空格后的数字）
    for %%b in (%%a) do set "PID=%%b"
    
    REM 验证 PID 是否为数字
    echo !PID!| findstr /r "^[0-9][0-9]*$" >nul
    if !errorlevel! equ 0 (
        echo [⚔️]  正在终止 PID !PID! ...
        taskkill /F /PID !PID! >nul 2>&1
        if !errorlevel! equ 0 (
            echo   ✅ 已终止 PID !PID!
            set FOUND=1
        ) else (
            echo   ❌ 无法终止 PID !PID! (权限不足或进程已结束)
        )
    )
)

REM 方法2: 直接杀所有 python.exe 中与 uvicorn 相关的进程
echo [🔍] 检查残留的 uvicorn 进程...
tasklist /FI "IMAGENAME eq python.exe" 2>nul | findstr /i "python" >nul
if !errorlevel! equ 0 (
    for /f "tokens=2 delims=," %%a in ('wmic process where "name='python.exe' and commandline like '%%uvicorn%%'" get processid /format:csv 2^>nul ^| findstr /r "^[0-9]"') do (
        echo [⚔️]  正在终止 uvicorn/python PID %%a ...
        taskkill /F /PID %%a >nul 2>&1
        if !errorlevel! equ 0 (
            echo   ✅ 已终止 PID %%a
            set FOUND=1
        )
    )
)

REM 等待端口释放
set WAIT=0
:checkloop
netstat -ano 2>nul | findstr ":8000.*LISTENING" >nul
if !errorlevel! equ 0 (
    set /a WAIT+=1
    if !WAIT! GEQ 5 (
        echo [⚠️] 端口 8000 在 5 秒后仍未释放
    ) else (
        timeout /t 1 /nobreak >nul
        goto checkloop
    )
) else (
    if !FOUND! equ 1 (
        echo [✅] 端口 8000 已释放
    ) else (
        echo [ℹ️] 端口 8000 未被占用
    )
)

REM 方法3: 终极方案 — 如果上述都失败，暴力杀所有 python.exe
netstat -ano 2>nul | findstr ":8000.*LISTENING" >nul
if !errorlevel! equ 0 (
    echo [💀] 端口仍未释放，执行终极清理...
    taskkill /F /IM python.exe >nul 2>&1
    timeout /t 3 /nobreak >nul
)

echo.
echo 按任意键退出...
pause >nul
