"""
简化启动脚本 - 绕过复杂初始化
"""
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

print("=" * 70)
print("联盟拓荒者 - 简化启动")
print("=" * 70)
print()

# 设置环境变量
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HUGGINGFACE_HUB_CACHE'] = os.path.expanduser('~/.cache/huggingface/hub')
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

print("启动服务...")
print()
print("访问地址:")
print("  - 主页: http://localhost:8000/")
print("  - API文档: http://localhost:8000/docs")
print()
print("按 Ctrl+C 停止")
print("=" * 70)
print()

# 直接导入并运行
import uvicorn
from backend.main import app

uvicorn.run(
    app,
    host="0.0.0.0",
    port=8000,
    log_level="info"
)