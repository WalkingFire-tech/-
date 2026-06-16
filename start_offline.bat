@echo off
chcp 65001 >nul
echo ========================================
echo   联盟拓荒者启动脚本
echo ========================================
echo.

REM 设置离线模式（避免HuggingFace下载）
set OFFLINE_MODE=true
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1

echo [1/3] 检查Ollama服务...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ⚠️  Ollama服务未启动
    echo.
    echo 请先启动Ollama:
    echo   1. 打开新终端
    echo   2. 运行: ollama serve
    echo   3. 等待服务启动后，重新运行此脚本
    echo.
    echo 或者继续使用Mock模式（仅用于测试）:
    echo   - 无法调用实际LLM
    echo   - 仅测试系统框架
    echo.
    choice /C YN /M "是否继续使用Mock模式"
    if errorlevel 2 exit /b 1
) else (
    echo ✅ Ollama服务已启动
)

echo.
echo [2/3] 检查依赖...
python -c "import fastapi; import uvicorn; print('✅ FastAPI已安装')" 2>nul
if %errorlevel% neq 0 (
    echo 安装依赖...
    pip install fastapi uvicorn loguru pyyaml python-dotenv aiohttp
)

echo.
echo [3/3] 启动后端服务...
echo.
echo 离线模式: 已启用（使用本地缓存的模型）
echo 访问地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo.
echo 按 Ctrl+C 停止服务
echo ========================================
echo.

python backend/main.py