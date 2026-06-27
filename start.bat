@echo off
chcp 65001 >nul
title 联盟拓荒者 - 完整功能启动

echo.
echo ========================================
echo 联盟拓荒者 - 完整功能启动
echo ========================================
echo.

cd /d "%~dp0"

REM 检查端口
echo [1/2] 检查端口...
netstat -ano | findstr ":8000.*LISTENING" >nul
if not errorlevel 1 (
    echo   端口8000已被占用，尝试结束占用进程...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
)
echo   ✓ 端口就绪

echo.
echo [2/2] 启动完整后端服务...
echo.
echo ========================================
echo 服务地址: http://localhost:8000/
echo API文档: http://localhost:8000/docs
echo.
echo 核心模块:
echo   ✓ 系统编排器
echo   ✓ 认知循环
echo   ✓ 反思管道
echo   ✓ 经验池
echo   ✓ 学习引擎
echo   ✓ 六层架构 (L0-L6)
echo   ✓ 七大机制
echo   ✓ 金丝雀验证器
echo   ✓ 记忆巩固器
echo ========================================
echo.
echo 正在启动...
echo.

REM 启动服务并自动打开浏览器
start "" http://localhost:8000/

python -m uvicorn backend.main_fast:app --host 0.0.0.0 --port 8000 --reload

pause
