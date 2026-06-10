@echo off
echo ========================================
echo 联盟拓荒者 - 前端启动
echo ========================================
echo.

REM 检查Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未安装Node.js
    echo 请先安装Node.js 18+: https://nodejs.org/
    pause
    exit /b 1
)

REM 检查frontend目录
if not exist "..\frontend" (
    echo 错误: frontend目录不存在
    echo 请先初始化Tauri项目:
    echo   npm create tauri-app@latest frontend
    pause
    exit /b 1
)

cd ..\frontend

REM 检查依赖
if not exist "node_modules" (
    echo 安装前端依赖...
    call npm install
)

echo.
echo 启动Tauri开发服务器...
echo.

call npm run tauri dev

pause