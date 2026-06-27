@echo off
chcp 65001 >nul
echo ========================================
echo 联盟拓荒者 - 启动并测试
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] 运行端到端测试...
python scripts\verification\simple_e2e_test.py
if errorlevel 1 (
    echo.
    echo ❌ 端到端测试失败
    pause
    exit /b 1
)

echo.
echo [2/2] 启动服务...
echo.
echo ========================================
echo 服务启动中...
echo.
echo 访问地址:
echo   - 主页: http://localhost:8000/
echo   - API文档: http://localhost:8000/docs
echo   - 学习仪表盘: http://localhost:8000/learning
echo.
echo 按 Ctrl+C 停止服务
echo ========================================
echo.

start http://localhost:8000/

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

pause