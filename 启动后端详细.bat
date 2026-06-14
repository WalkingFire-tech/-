@echo off
chcp 65001 >nul
echo ============================================================
echo 启动联盟拓荒者后端服务
echo ============================================================
echo.

echo [检查] Python环境...
python --version
echo.

echo [检查] 端口8000...
netstat -ano | findstr ":8000" | findstr "LISTENING"
if %errorlevel% equ 0 (
    echo 警告: 端口8000已被占用
    echo.
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
        echo 正在停止进程 %%a...
        taskkill /PID %%a /F >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
) else (
    echo 端口8000可用
)
echo.

echo [启动] 后端服务...
echo 地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo.

start "联盟拓荒者后端" cmd /k "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

echo 等待服务启动...
ping 127.0.0.1 -n 6 >nul

echo.
echo ============================================================
echo 启动完成！
echo ============================================================
echo.
echo 后端地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo.
echo 按任意键退出（后端将继续运行）
pause