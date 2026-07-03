@echo off
chcp 65001 >nul
echo ====================================
echo 联盟拓荒者 - 学习系统启动
echo ====================================
echo.

echo [1/3] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装或未添加到PATH
    pause
    exit /b 1
)
echo ✅ Python环境正常

echo.
echo [2/3] 检查依赖...
python -c "import watchdog; import fastapi; import yaml" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  正在安装依赖...
    pip install watchdog pyyaml fastapi uvicorn loguru
)
echo ✅ 依赖检查完成

echo.
echo [3/3] 启动后端服务...
echo.
echo ====================================
echo 服务地址:
echo   - 主页面: http://localhost:8000
echo   - 学习仪表盘: http://localhost:8000/learning
echo   - API文档: http://localhost:8000/docs
echo ====================================
echo.
echo 按 Ctrl+C 停止服务
echo.

python -m uvicorn backend.main_fast:app --host 0.0.0.0 --port 8000