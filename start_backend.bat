@echo off
chcp 65001 >nul
echo ========================================
echo 联盟拓荒者 - 启动后端服务
echo ========================================
echo.

REM 设置镜像站点环境变量
set HF_ENDPOINT=https://hf-mirror.com
set HUGGINGFACE_HUB_CACHE=%USERPROFILE%\.cache\huggingface\hub
set HF_HUB_DISABLE_TELEMETRY=1
set TRANSFORMERS_VERBOSITY=error

echo [环境配置]
echo HF_ENDPOINT: %HF_ENDPOINT%
echo CACHE: %HUGGINGFACE_HUB_CACHE%
echo.

echo [启动服务]
python backend/main.py

pause