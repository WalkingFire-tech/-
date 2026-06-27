@echo off
chcp 65001 >nul
echo ========================================
echo 测试镜像配置
echo ========================================
echo.

REM 设置镜像站点环境变量
set HF_ENDPOINT=https://hf-mirror.com
set HUGGINGFACE_HUB_CACHE=%USERPROFILE%\.cache\huggingface\hub
set HF_HUB_DISABLE_TELEMETRY=1
set TRANSFORMERS_VERBOSITY=error

echo [环境变量]
echo HF_ENDPOINT: %HF_ENDPOINT%
echo.

echo [检查huggingface_hub]
python -c "import huggingface_hub.constants as c; print('HUGGINGFACE_CO_URL_HOME:', c.HUGGINGFACE_CO_URL_HOME)"

echo.
echo [检查向量检索器]
python -c "import sys; sys.path.insert(0, '.'); from core.vector_retriever import EMBEDDING_AVAILABLE; print('EMBEDDING_AVAILABLE:', EMBEDDING_AVAILABLE)"

echo.
echo ========================================
echo 测试完成
echo ========================================
echo.
echo 如果仍出现huggingface.co错误，请重启后端服务

pause