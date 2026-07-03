@echo off
chcp 65001 >nul
echo ========================================
echo 端到端测试
echo ========================================
echo.

REM 设置环境变量
set HF_ENDPOINT=https://hf-mirror.com
set HUGGINGFACE_HUB_CACHE=%USERPROFILE%\.cache\huggingface\hub
set HF_HUB_DISABLE_TELEMETRY=1
set TRANSFORMERS_VERBOSITY=error

echo [测试1] 检查镜像配置
python -c "import sys; sys.path.insert(0, '.'); from core.hf_mirror_patch import *; import huggingface_hub.constants as c; print('镜像URL:', c.HUGGINGFACE_CO_URL_HOME)"

echo.
echo [测试2] 检查向量检索器
python -c "import sys; sys.path.insert(0, '.'); from core.vector_retriever import EMBEDDING_AVAILABLE; print('EMBEDDING_AVAILABLE:', EMBEDDING_AVAILABLE)"

echo.
echo [测试3] 测试后端API
python -c "import sys; sys.path.insert(0, '.'); from fastapi.testclient import TestClient; from backend.main import app; client = TestClient(app); r = client.post('/api/models/reload'); print('刷新API:', r.json().get('success'), '-', r.json().get('message'))"

echo.
echo [测试4] 检查前端代码
findstr /C:"refreshModels(event)" frontend\app.js >nul && echo ✓ refreshModels函数正确 || echo ✗ refreshModels函数错误
findstr /C:"ollama_status" frontend\app.js >nul && echo ✓ ollama_status检查存在 || echo ✗ ollama_status检查缺失
findstr /C:"v3.1.3" frontend\index.html >nul && echo ✓ 版本号v3.1.3 || echo ✗ 版本号错误

echo.
echo ========================================
echo 测试完成
echo ========================================
echo.
echo 如果所有测试通过，请:
echo 1. 重启后端服务（使用 start_backend.bat）
echo 2. 打开浏览器测试刷新按钮
echo 3. 检查是否还有 huggingface.co 连接错误

pause