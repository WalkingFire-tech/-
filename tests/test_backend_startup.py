"""测试后端启动"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

print("1. 测试配置管理器...")
from infrastructure.config_manager import config
print(f"✓ 配置加载成功: {list(config._config.keys())}")

print("\n2. 测试工具生成器...")
from tools.generator import ToolGenerator
tg = ToolGenerator()
print(f"✓ 工具生成器初始化成功: {tg.generated_tools_dir}")

print("\n3. 测试FastAPI应用...")
from backend.main import app
print(f"✓ FastAPI应用创建成功: {app.title}")

print("\n4. 测试API端点...")
from fastapi.testclient import TestClient
client = TestClient(app)
response = client.get("/api/health")
print(f"✓ 健康检查: {response.json()}")

print("\n✅ 所有测试通过！后端可以正常启动")