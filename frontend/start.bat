@echo off
chcp 65001 >nul
echo ========================================
echo 联盟拓荒者 - 前端界面
echo ========================================
echo.
echo 启动前端界面...
echo 访问地址: http://localhost:8000/frontend/index.html
echo.
echo 提示: 请确保后端服务已启动
echo.

start "" "%~dp0index.html"

pause