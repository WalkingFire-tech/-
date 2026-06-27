@echo off
chcp 65001 >nul
echo ========================================
echo 联盟拓荒者 - 启动服务
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] 检查Python环境...
python --version
if errorlevel 1 (
    echo ❌ Python未安装或未添加到PATH
    pause
    exit /b 1
)

echo.
echo [2/2] 启动后端服务...
echo.
echo 访问地址:
echo   - 主页: http://localhost:8000/
echo   - API文档: http://localhost:8000/docs
echo   - 学习仪表盘: http://localhost:8000/learning
echo.
echo 按 Ctrl+C 停止服务
echo ========================================
echo.

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

pause
