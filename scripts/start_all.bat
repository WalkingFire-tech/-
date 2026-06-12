@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo 联盟拓荒者 - 完整启动
echo ========================================
echo.

REM 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo 激活虚拟环境...
    call venv\Scripts\activate.bat
) else (
    echo 使用系统Python
)

echo.
echo [1/2] 启动后端服务...
echo 后端地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo.

start "后端服务" cmd /k "python -m uvicorn api:app --reload --port 8000"

echo 等待后端启动...
timeout /t 3 /nobreak >nul

echo.
echo [2/2] 打开前端界面...
echo 前端地址: http://localhost:8000/
echo.

start http://localhost:8000/

echo.
echo ========================================
echo 启动完成！
echo ========================================
echo.
echo 后端API: http://localhost:8000/docs
echo 前端界面: http://localhost:8000/
echo.
echo 按任意键退出（后端将继续运行）
echo.

pause
