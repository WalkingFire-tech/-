@echo off
echo ========================================
echo 联盟拓荒者 - 完整系统启动
echo ========================================
echo.

echo [1/2] 启动后端服务...
start "后端服务" cmd /k "scripts\start_backend.bat"

timeout /t 5 /nobreak >nul

echo [2/2] 启动前端服务...
start "前端服务" cmd /k "scripts\start_frontend.bat"

echo.
echo ========================================
echo 系统已启动！
echo ========================================
echo.
echo 后端地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo 前端窗口: 自动打开
echo.
echo 按任意键退出此窗口（服务将继续运行）
pause >nul